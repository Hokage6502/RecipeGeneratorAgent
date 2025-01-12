# Major improvement - retry on failure and added steps

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
        'You are an AI chef. Your task is to create recipes based on available ingredients and user preferences. '
        'Make sure to include all ingredients provided by the user in the recipe, even if you suggest additional ingredients. '
        'The ingredients specified by the user must always be included in the recipe, regardless of whether they are in the available ingredients. '
        'Also, be creative and innovative with the recipe names and suggestions.'
    ),
)


# Tool to extract available ingredients from user inputs
@recipe_agent.tool
async def extract_ingredients(ctx: RunContext[Deps]) -> List[str]:
    """Extract ingredients based on user inputs."""
    # Make sure to always include the specific ingredients the user provided
    return ctx.deps.specific_ingredients


# Result Validator: Ensure that the generated recipe matches the user preferences
@recipe_agent.result_validator
async def validate_recipe_result(
    ctx: RunContext[Deps], result: Union[RecipeDetails, NoRecipeFound]
) -> Union[RecipeDetails, NoRecipeFound]:
    """Validate that the generated recipe meets the user's requirements."""
    if isinstance(result, NoRecipeFound):
        # Instead of returning NoRecipeFound, continue retrying
        logger.info('No recipe found, retrying...')
        return ModelRetry('No recipe found, retrying with the same input.')

    errors: list[str] = []
    if not result.ingredients:
        errors.append("Recipe must have ingredients.")
    if not result.steps:
        errors.append("Recipe must have steps.")

    if errors:
        raise ModelRetry('\n'.join(errors))
    else:
        return result


# Function to read ingredients from Excel
def get_available_ingredients(file_path):
    df = pd.read_excel(file_path)
    return df['Ingredient'].dropna().tolist()

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

    # run the recipe generation agent until a valid recipe is found
    while True:
        # Log the prompt being sent to the agent
        prompt = f'Generate a recipe with the following specific ingredients: {", ".join(deps.specific_ingredients)} and preferences: {deps.user_inputs}. Ensure that all user-provided ingredients are included. Be creative and innovative with the recipe name.'
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
                print(f'Steps: {", ".join(recipe.steps)}')

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

if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
