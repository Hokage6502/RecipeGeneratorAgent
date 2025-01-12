import json
import os
import openai
import logging
import asyncio
import pandas as pd
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.messages import ModelMessage
from pydantic import BaseModel
from typing import List, Union
from dataclasses import dataclass
import logfire

logfire.configure()

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    raise EnvironmentError("OPENAI_API_KEY not found. Please set it in environment variables.")

# Configure logging with rotation
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("recipe_generation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# Recipe Details Model
class RecipeDetails(BaseModel):
    recipe_name: str
    ingredients: List[str]
    steps: List[str]
    step_times: List[str]

class NoRecipeFound(BaseModel):
    pass

@dataclass
class Deps:
    available_ingredients: List[str]
    user_inputs: dict
    specific_ingredients: List[str]

# Recipe generation agent
recipe_agent = Agent[Deps, Union[RecipeDetails, NoRecipeFound]](
    model='openai:gpt-4o-mini',
    system_prompt='''
        You are an AI Chef creating recipes based on user preferences and available ingredients. 
        Select the best ingredients to craft an innovative, simple, and clear recipe respecting dietary requirements.
    '''
)

# Tool: Extract ingredients
@recipe_agent.tool
async def extract_ingredients(ctx: RunContext[Deps]) -> List[str]:
    return ctx.deps.specific_ingredients

# Result validator for recipe validation
@recipe_agent.result_validator
async def validate_recipe_result(ctx: RunContext[Deps], result: Union[RecipeDetails, NoRecipeFound]) -> Union[RecipeDetails, NoRecipeFound]:
    if isinstance(result, NoRecipeFound):
        logger.info('No valid recipe found, retrying...')
        return ModelRetry("Retry due to no recipe found.")
    
    missing_ingredients = [i for i in ctx.deps.specific_ingredients if i not in result.ingredients]
    if missing_ingredients:
        raise ModelRetry(f"Missing required ingredients: {', '.join(missing_ingredients)}")
    
    if not result.ingredients or not result.steps:
        raise ModelRetry("Incomplete recipe data detected.")
    
    return result

# Helper: Generate recipe prompt
def generate_recipe_prompt(diet: str, cuisine: str, specific_ingredients: List[str], available_ingredients: List[str]) -> str:
    return f'''
    **Diet:** {diet}
    **Cuisine:** {cuisine}
    **Specific Ingredients:** {", ".join(specific_ingredients)}
    **Available Ingredients:** {", ".join(available_ingredients)}
    '''

# Helper: Read ingredients from Excel
def get_available_ingredients(file_path: str) -> List[str]:
    try:
        df = pd.read_excel(file_path)
        return df['Ingredient'].dropna().tolist()
    except FileNotFoundError:
        logger.error(f"Excel file not found at {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error reading ingredients: {e}")
        return []

# Main function to run recipe generation
async def generate_recipe():
    # Mock input for testing; replace with sys.argv or user inputs in production
    diet = "vegetarian"
    cuisine = "Italian"
    specific_ingredients = ["tomato", "basil", "mozzarella"]
    available_ingredients = get_available_ingredients("ingredients.xlsx")

    deps = Deps(
        available_ingredients=available_ingredients,
        user_inputs={"diet": diet, "cuisine": cuisine},
        specific_ingredients=specific_ingredients
    )

    while True:
        prompt = generate_recipe_prompt(diet, cuisine, specific_ingredients, available_ingredients)
        logger.debug(f"Generated prompt: {prompt.strip()}")

        try:
            result = await recipe_agent.run(prompt, deps=deps)
            recipe = result.data
            
            if isinstance(recipe, NoRecipeFound):
                logger.info("No recipe found, generating another...")
                continue
            
            logger.info(f"Recipe generated: {recipe.recipe_name}")
            print(f"Recipe Name: {recipe.recipe_name}")
            print("Ingredients:", ", ".join(recipe.ingredients))
            print("Steps:")
            for idx, (step, time) in enumerate(zip(recipe.steps, recipe.step_times), 1):
                print(f"{idx}. {step} (Time: {time})")

            # User choice to continue or finalize
            if input("Finalize recipe? (yes/no): ").strip().lower() == 'yes':
                logger.info("Recipe finalized successfully.")
                break

        except ModelRetry as retry:
            logger.warning(f"Retry triggered: {retry}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            break

if __name__ == "__main__":
    asyncio.run(generate_recipe())
