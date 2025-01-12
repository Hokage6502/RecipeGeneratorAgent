import json
import sys
import openai
import os
from dotenv import load_dotenv
import logging
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import Usage
from typing import List, Union
from pydantic import BaseModel
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='recipe_generation.log', format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# RecipeDetails Model
class RecipeDetails(BaseModel):
    recipe_name: str
    ingredients: List[str]
    steps: List[str]
    step_times: List[str]

class NoRecipeFound(BaseModel):
    pass

# Dependencies for generating the recipe
@dataclass
class Deps:
    available_ingredients: List[str]
    user_inputs: dict
    specific_ingredients: List[str]

# User Prompt
user_prompt = '''
    You are an AI Chef tasked with creating a recipe based on the available ingredients and preferences provided by the user. You do **not** need to use every ingredient given; instead, build a creative and unique recipe by selecting ingredients from the provided list that would work well together. Ensure the recipe respects the user's preferences (e.g., vegetarian, no eggs, etc.).

    **Guidelines:**
        1. You are free to choose a selection of ingredients from the provided list to create a balanced and innovative recipe.
        2. You do **not** need to use all of the ingredients in the recipe. Instead, choose the ingredients that complement each other and the user's preferences.
        3. If new ingredients are added, explain their necessity and ensure they align with the user's preferences (e.g., vegetarian, no eggs, etc.).
        4. Format the steps as follows:
        - 1. Step description (Time: x min)
        - 2. Step description (Time: x min)
        - 3. Step description (Time: x min)
        Ensure there is no repetition of step numbers, and time is only mentioned once per step.
        5. The recipe should be simple, clear, and easy to follow while respecting the user's preferences.
        6. If any ingredient is not suitable or doesn’t fit with the preferences (e.g., vegetarian, no eggs), explain why and suggest an alternative if needed.

    **Diet**: {diet}
    **Cuisine**: {cuisine}
    **Available Ingredients**: {available_ingredients}

    Please ensure that the recipe is creative, respects the given preferences, and uses the provided ingredients in an innovative way. However, feel free to omit ingredients if they don't fit the recipe.
'''

# Recipe generation agent using GPT-4
recipe_agent = Agent[Deps, Union[RecipeDetails, NoRecipeFound]](
    'openai:gpt-4o-mini',  
    result_type=Union[RecipeDetails, NoRecipeFound],
    system_prompt='''  
        You are a skilled AI Chef capable of creating unique and creative recipes based on the user's preferences and available ingredients. Your goal is to build a recipe that respects the user's dietary requirements and ingredient list, but you do not have to use all the ingredients provided. Instead, carefully choose the ingredients that will work best together to create a balanced and innovative dish.

        Guidelines:
            1. Consider the dietary preferences (e.g., vegetarian, vegan, no eggs) when selecting the ingredients for the recipe.
            2. You can choose any number of ingredients from the available list to craft a unique recipe.
            3. You do not need to include every ingredient in the recipe. Choose those that complement each other and the given dietary constraints.
            4. If any ingredients are unsuitable or not ideal for the recipe, explain why and suggest alternatives that fit the dietary needs.
            5. Ensure the recipe is clear, easy to follow, and visually appealing.
            6. For each step of the recipe, ensure the instructions are simple and concise with time estimates for each step.
            7. Avoid repeating steps, and be mindful of the ingredient quantities and instructions.

        Keep the recipe creative, straightforward, and focused on the available ingredients. Do not feel bound to use every ingredient in the list, but instead, build the best possible recipe based on the user's preferences.
''')

# Tool to extract ingredients from user input
@recipe_agent.tool
async def extract_ingredients(ctx: RunContext[Deps]) -> List[str]:
    """Extract the specific ingredients from the user input."""
    return ctx.deps.specific_ingredients

# Validate the recipe to meet user requirements
@recipe_agent.result_validator
async def validate_recipe_result(ctx: RunContext[Deps], result: Union[RecipeDetails, NoRecipeFound]) -> Union[RecipeDetails, NoRecipeFound]:
    if isinstance(result, NoRecipeFound):
        logger.info('No valid recipe found, retrying...')
        return ModelRetry('No recipe found, retrying...')
    
    errors = []
    if not result.ingredients:
        errors.append("Recipe must have ingredients.")
    if not result.steps:
        errors.append("Recipe must have steps.")
    if not all(ingredient in result.ingredients for ingredient in ctx.deps.specific_ingredients):
        errors.append(f"Missing ingredients: {', '.join(ctx.deps.specific_ingredients)}")
    
    if errors:
        raise ModelRetry('\n'.join(errors))
    return result

# Helper function to generate recipe prompt
def generate_recipe(diet, cuisine, specific_ingredients, available_ingredients):
    # Ensure ingredients are passed as comma-separated strings
    return user_prompt.format(
        specific_ingredients=', '.join(specific_ingredients),
        available_ingredients=', '.join(available_ingredients),
        diet=diet,
        cuisine=cuisine
    )

# Function to read available ingredients from Excel file
def get_available_ingredients(file_path):
    import pandas as pd
    df = pd.read_excel(file_path)
    return df['Ingredient'].dropna().tolist()

# Main recipe generation process
async def main():
    diet = sys.argv[1]  # Passed from Node.js
    cuisine = sys.argv[2]  # Passed from Node.js
    specific_ingredients = sys.argv[3]  # Passed from Node.js
    
    excel_path = "ingredients.xlsx"
    available_ingredients = get_available_ingredients(excel_path)
    
    user_inputs = {
        "diet": diet,
        "cuisine": cuisine,
        "specific_ingredients": specific_ingredients
    }
    
    deps = Deps(
        available_ingredients=available_ingredients,
        user_inputs=user_inputs,
        specific_ingredients=specific_ingredients
    )
    
    while True:
        prompt = generate_recipe(diet, cuisine, specific_ingredients, available_ingredients)
        logger.debug(f"Sending prompt: {prompt}")

        try:
            result = await recipe_agent.run(
                prompt,
                deps=deps,
                usage=Usage(),
                message_history=None
            )
            
            if isinstance(result.data, NoRecipeFound):
                logger.info('No recipe found, retrying...')
                continue
            else:
                recipe = result.data
                # print(json.dumps(recipe))
                logger.info(f"Recipe found: {recipe.recipe_name}")
                print(f"Recipe found: {recipe.recipe_name}")
                print(f"Ingredients: {', '.join(recipe.ingredients)}")
                print("Steps:")
                for idx, (step, time) in enumerate(zip(recipe.steps, recipe.step_times)):
                    print(f"{idx+1}. {step} (Time: {time})")
                
                # Ask user to finalize or generate another recipe
                answer = input("Do you want to finalize this recipe or generate another? (finalize/generate): ")
                if answer.lower() == 'finalize':
                    logger.info(f"Recipe finalized: {recipe.recipe_name}")
                    break
        except Exception as e:
            logger.error(f"Error generating recipe: {e}")
            print("Error generating recipe, please try again.")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

