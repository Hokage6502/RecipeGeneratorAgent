#Best prompts performace and output
#New ingredient added itself optimisation




from dataclasses import dataclass
import datetime
import sys
import openai
import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.messages import ModelMessage
from rich.prompt import Prompt
from typing import Literal, List, Union
from dotenv import load_dotenv
import os
import logging
from pydantic_ai.usage import Usage

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='recipe_generation.log', 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Load environment variables from .env
load_dotenv()

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Define RecipeDetails for the recipe generation
class RecipeDetails(BaseModel):
    """Details of the generated recipe."""
    recipe_name: str
    ingredients: List[str]
    steps: List[str]
    step_times: List[str]  # Time taken for each step


class NoRecipeFound(BaseModel):
    """When no valid recipe is found."""

# Dependencies for generating the recipe (using Python inputs)
@dataclass
class Deps:
    available_ingredients: List[str]
    user_inputs: dict
    specific_ingredients: List[str]  # Separate specific ingredients

# This agent is responsible for controlling the flow of recipe generation.
recipe_agent = Agent[Deps, Union[RecipeDetails, NoRecipeFound]](
    'openai:gpt-4o-mini',  # Use GPT-4 model for recipe generation
    result_type=Union[RecipeDetails, NoRecipeFound],  # type: ignore
    system_prompt=(
        '''  
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
        '''
        # "You are an AI Chef tasked with creating recipes based on the specific ingredients and preferences provided by the user. Please ensure that most of ingredients provided by the user are included in the recipe. Additionally, respect the user's preferences (e.g., vegetarian, no eggs, etc.). "

        # "**Guidelines:**"
        # "1. Do **not** include any extra ingredients unless absolutely necessary. If you must include additional ingredients, list them separately and explain why they are essential."
        # "2. If additional ingredients are not required, innovate using the available ingredients to create a unique recipe."
        # "3. Always include all the ingredients provided by the user."
        # "4. If new ingredients are added, explain their necessity and ensure they are not part of the provided list."
        # "5. Format the steps as follows: 1. Step description (Time: x minutes). Only mention time once per step and do not repeat step numbers."
        # "6. Keep the recipe clear, creative, and easy to follow."

        # "Do not repeat the number for each step, and ensure time is only mentioned once per step."

        # # 'You are an AI chef. Your task is to create recipes based on available ingredients and user preferences. '
        # # 'Make sure to include all ingredients provided by the user in the recipe, even if you suggest additional ingredients. '
        # # 'The ingredients specified by the user must always be included in the recipe, regardless of whether they are in the available ingredients. '
        # # 'Only add additional ingredients when absolutely necessary. If you add new ingredients, please list them and ensure they are not part of the available ingredients or provided list. '
        # # 'Please also estimate a time for each step and format the steps as 1. 2. 3. with the time for each step listed next to the action. '
        # # 'Do not repeat the number for each step, and do not include time multiple times for the same step.'
    ),
)

# Tool to extract available ingredients from user inputs
@recipe_agent.tool
async def extract_ingredients(ctx: RunContext[Deps]) -> List[str]:
    """Extract ingredients based on user inputs."""
    # Always include the specific ingredients the user provided
    return ctx.deps.specific_ingredients

# Result Validator: Ensure that the generated recipe matches the user preferences
@recipe_agent.result_validator
async def validate_recipe_result(
    ctx: RunContext[Deps], result: Union[RecipeDetails, NoRecipeFound]
) -> Union[RecipeDetails, NoRecipeFound]:
    """Validate that the generated recipe meets the user's requirements."""
    if isinstance(result, NoRecipeFound):
        # Retry until a valid recipe is found
        logger.info('No recipe found, retrying...')
        return ModelRetry('No recipe found, retrying with the same input.')

    errors: list[str] = []
    if not result.ingredients:
        errors.append("Recipe must have ingredients.")
    if not result.steps:
        errors.append("Recipe must have steps.")

    # Ensure all ingredients specified by the user are included
    if not all(ingredient in result.ingredients for ingredient in ctx.deps.specific_ingredients):
        errors.append(f"Not all specific ingredients were included. Missing ingredients: {', '.join(ctx.deps.specific_ingredients)}")

    if errors:
        raise ModelRetry('\n'.join(errors))
    else:
        return result

# Function to read ingredients from Excel
def get_available_ingredients(file_path):
    df = pd.read_excel(file_path)
    return df['Ingredient'].dropna().tolist()

def generate_recipe(diet, cuisine, specific_ingredients, available_ingredients):
    # Start building the recipe prompt
    prompt = f'''
    
    You are an AI Chef tasked with creating recipes based on the specific ingredients and preferences provided by the user. Please ensure that ingredients provided by the user are included in the recipe. Additionally, respect the user's preferences (e.g., vegetarian, no eggs, etc.).

    **Guidelines:**
    1. You are free to choose a selection of ingredients from the provided list to create a balanced and innovative recipe. Choose the ingredients that complement each other and the user's preferences.
    2. Do **not** include any extra ingredients unless absolutely necessary. If you must include additional ingredients, list them separately and explain their necessity and ensure they align with the user's preferences (e.g., vegetarian, no eggs, etc.).
    3. If additional ingredients are not needed, innovate using the available ingredients to create a unique recipe.
    4. Format the steps as follows:
       - Step description Time: x min
       - Step description Time: x min
       - Step description Time: x min
       Ensure there is no repetition of step numbers and time is only mentioned once for each step.
    6. Keep the recipe simple, clear, and easy to follow while respecting the user preferences (e.g., vegetarian, no eggs, etc.).

    **Specific Ingredients**: {', '.join(specific_ingredients)}
    **Available Ingredients**: {', '.join(available_ingredients)}
    **Diet**: {diet}
    **Cuisine**: {cuisine}

    Please make sure the recipe is creative, respects the given preferences, and uses the provided ingredients in an innovative way.However, feel free to omit ingredients if they don't fit the recipe.
    '''
    return prompt

# Main Recipe generation flow
async def main():
    # Example list of available ingredients and user inputs
    diet = sys.argv[1]
    cuisine = sys.argv[2]
    specific_ingredients = sys.argv[3].split(",")  # Convert comma-separated string into a list

    # Load available ingredients from Excel
    excel_path = "ingredients.xlsx"  # Path to the Excel file
    available_ingredients = get_available_ingredients(excel_path)

    user_inputs = {
        "diet": diet,
        "cuisine": cuisine,
        "specific_ingredients": specific_ingredients
    }

    deps = Deps(
        available_ingredients=available_ingredients,
        user_inputs=user_inputs,
        specific_ingredients=specific_ingredients  # Include the specific ingredients separately
    )
    
    message_history: list[ModelMessage] | None = None
    usage = Usage()

    # Keep track of any additional ingredients added by the model
    missing_ingredients = []

    # Run the recipe generation agent until a valid recipe is found
    while True:
        # Log the prompt being sent to the agent
        prompt = generate_recipe(diet, cuisine, specific_ingredients, available_ingredients)
        # prompt = f'Generate a recipe with the following specific ingredients: {", ".join(deps.specific_ingredients)} and preferences: {deps.user_inputs}. Ensure that all user-provided ingredients are included. Only add additional ingredients if absolutely necessary; otherwise, innovate with the available ingredients. If any new ingredients are used, list them separately and explain why they were needed, ensuring they are not part of the provided list.Please follow these guidelines:1. Ensure that **all** user-provided ingredients are included in the recipe.2. Do **not** add extra ingredients unless absolutely necessary. If additional ingredients are added, list them and explain why they were required.3. If additional ingredients are not needed, use creativity and innovate with the available ingredients to craft a unique recipe.4. Format the steps as follows:- 1. Step description (Time: x min) Ensure there is no repetition of step numbers and time is only mentioned once for each step. 5. Keep the recipe simple, clear, and easy to follow while respecting the user preferences (e.g., vegetarian, no eggs, etc.). Please make sure the recipe is creative, respects the given preferences, and uses the provided ingredients in an innovative way.'
        # f'Generate a recipe with the following specific ingredients: {", ".join(deps.specific_ingredients)} and preferences: {deps.user_inputs}. Ensure that all user-provided ingredients are included. Only add additional ingredients if absolutely necessary else try to innvoate with available ingredients and if using additional list any new ingredients that are not in the provided list. Please provide times for each step and format the steps as 1. 2. 3. without repeating step numbers, and include time only once in the format (Time: x min).'
        logger.debug(f"Sending prompt to model: {prompt}")

        try:
            result = await recipe_agent.run(
                prompt,
                deps=deps,
                usage=usage,
                message_history=message_history,
            )

            if isinstance(result.data, NoRecipeFound):
                # Retry until a valid recipe is found
                logger.info('No recipe found, retrying...')
                print('No recipe found, retrying...')
                continue
            else:
                recipe = result.data
                # Log the successful result
                logger.info(f'Recipe found: {recipe.recipe_name}')
                print(f'Recipe found: {recipe.recipe_name}')
                print(f'Ingredients: {", ".join(recipe.ingredients)}')

                # Log missing ingredients (if any)
                new_ingredients = [ingredient for ingredient in recipe.ingredients if ingredient not in deps.specific_ingredients and ingredient not in available_ingredients]
                if new_ingredients:
                    missing_ingredients.extend(new_ingredients)
                    logger.info(f"New ingredients added to the recipe: {', '.join(new_ingredients)}")
                    print(f"New ingredients added by the model: {', '.join(new_ingredients)}")
                    
                # List steps with time for each step, ensuring time is formatted correctly
                print("Steps:")
                for idx, (step, time) in enumerate(zip(recipe.steps, recipe.step_times)):
                    # Ensure no repetition of time formatting
                    clean_time = time.replace("Time:", "").strip() if "Time:" in time else time.strip()
                    print(f"{idx+1}. {step} (Time: {clean_time})")

                # Simulating user decision on whether to finalize the recipe
                answer = Prompt.ask(
                    'Do you want to finalize this recipe, or generate another one? (finalize/*generate) ',
                    choices=['finalize', 'generate', ''],
                    show_choices=False,
                )
                if answer == 'finalize':
                    logger.info(f'Recipe finalized: {recipe.recipe_name}')
                    print(f'Recipe finalized: {recipe.recipe_name}')
                    break
                else:
                    message_history = result.all_messages(
                        result_tool_return_content='Please suggest another recipe'
                    )

        except Exception as e:
            logger.error(f"Error during recipe generation: {e}")
            print("Error generating recipe. Please try again.")

    # Log all missing ingredients after the generation is done
    if missing_ingredients:
        logger.info(f"Missing ingredients that were added: {', '.join(missing_ingredients)}")

if __name__ == '__main__':
    import asyncio

    asyncio.run(main())