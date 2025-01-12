# # Importing necessary libraries
# from dataclasses import dataclass
# import openai
# import os
# from dotenv import load_dotenv
# import logging
# from pydantic_ai import Agent, RunContext, ModelRetry
# from pydantic_ai.messages import ModelMessage
# from pydantic_ai.usage import Usage
# from typing import List, Union
# from pydantic import BaseModel

# # Configure logging
# logging.basicConfig(level=logging.DEBUG, filename='recipe_generation.log', format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger()

# # Load environment variables
# load_dotenv()
# openai.api_key = os.getenv("OPENAI_API_KEY")

# system_prompt = """
# You are an AI Chef tasked with creating recipes using the user-provided ingredients. Ensure that all specified ingredients are included in the recipe and respect the user's dietary preferences (e.g., vegetarian, no eggs, etc.).

# **Guidelines:**
# 1. Avoid adding extra ingredients unless absolutely necessary. If extra ingredients are added, list them and explain why they are needed.
# 2. Innovate with the available ingredients to create a unique recipe if no additional ingredients are needed.
# 3. Always include all the user-specified ingredients.
# 4. If additional ingredients are added, explain their necessity and ensure they are not part of the provided list.
# 5. Format the steps as:  
#    - Step description (Time: x min). Ensure time is only mentioned once per step.

# Make the recipe clear, creative, and easy to follow, ensuring it respects the user’s preferences.
# """


# user_prompt = """
# You are an AI Chef tasked with creating a recipe using the provided ingredients. Ensure all specified ingredients are included and respect the user's preferences (e.g., vegetarian, no eggs, etc.).

# **Guidelines:**
# 1. Do not add extra ingredients unless necessary. If new ingredients are included, list and explain why they are required.
# 2. If no additional ingredients are needed, use the available ingredients to create an innovative recipe.
# 3. Always include all the ingredients provided by the user.
# 4. If new ingredients are used, ensure they are not part of the provided list and explain their necessity.
# 5. Format the steps as:  
#    - Step description (Time: x min). Ensure time is mentioned only once per step.

# **Specific Ingredients**: {', '.join(specific_ingredients)}
# **Available Ingredients**: {', '.join(available_ingredients)}
# **Diet**: {diet}
# **Cuisine**: {cuisine}

# Create a simple, creative, and easy-to-follow recipe that respects the user’s preferences.
# """


# # RecipeDetails Model
# class RecipeDetails(BaseModel):
#     recipe_name: str
#     ingredients: List[str]
#     steps: List[str]
#     step_times: List[str]

# class NoRecipeFound(BaseModel):
#     pass

# # Dependencies for generating the recipe
# @dataclass
# class Deps:
#     available_ingredients: List[str]
#     user_inputs: dict
#     specific_ingredients: List[str]

# # Recipe generation agent using GPT-4
# recipe_agent = Agent[Deps, Union[RecipeDetails, NoRecipeFound]](
#     'openai:gpt-4o-mini',  
#     result_type=Union[RecipeDetails, NoRecipeFound],
#     system_prompt=system_prompt
# )

# # Tool to extract ingredients from user input
# @recipe_agent.tool
# async def extract_ingredients(ctx: RunContext[Deps]) -> List[str]:
#     """Extract the specific ingredients from the user input."""
#     return ctx.deps.specific_ingredients

# # Validate the recipe to meet user requirements
# @recipe_agent.result_validator
# async def validate_recipe_result(ctx: RunContext[Deps], result: Union[RecipeDetails, NoRecipeFound]) -> Union[RecipeDetails, NoRecipeFound]:
#     if isinstance(result, NoRecipeFound):
#         logger.info('No valid recipe found, retrying...')
#         return ModelRetry('No recipe found, retrying...')
    
#     errors = []
#     if not result.ingredients:
#         errors.append("Recipe must have ingredients.")
#     if not result.steps:
#         errors.append("Recipe must have steps.")
#     if not all(ingredient in result.ingredients for ingredient in ctx.deps.specific_ingredients):
#         errors.append(f"Missing ingredients: {', '.join(ctx.deps.specific_ingredients)}")
    
#     if errors:
#         raise ModelRetry('\n'.join(errors))
#     return result

# # Helper function to generate recipe prompt
# def generate_recipe(diet, cuisine, specific_ingredients, available_ingredients):
#     return user_prompt.format(
#         specific_ingredients=specific_ingredients,
#         available_ingredients=available_ingredients,
#         diet=diet,
#         cuisine=cuisine
#     )

# # Function to read available ingredients from Excel file
# def get_available_ingredients(file_path):
#     import pandas as pd
#     df = pd.read_excel(file_path)
#     return df['Ingredient'].dropna().tolist()

# # Main recipe generation process
# async def main():
#     diet = 'vegetarian'
#     cuisine = 'Mexican'
#     specific_ingredients = ['Mango']
    
#     excel_path = "ingredients.xlsx"
#     available_ingredients = get_available_ingredients(excel_path)
    
#     user_inputs = {
#         "diet": diet,
#         "cuisine": cuisine,
#         "specific_ingredients": specific_ingredients
#     }
    
#     deps = Deps(
#         available_ingredients=available_ingredients,
#         user_inputs=user_inputs,
#         specific_ingredients=specific_ingredients
#     )
    
#     while True:
#         prompt = generate_recipe(diet, cuisine, specific_ingredients, available_ingredients)
#         logger.debug(f"Sending prompt: {prompt}")

#         try:
#             result = await recipe_agent.run(
#                 prompt,
#                 deps=deps,
#                 usage=Usage(),
#                 message_history=None
#             )
            
#             if isinstance(result.data, NoRecipeFound):
#                 logger.info('No recipe found, retrying...')
#                 continue
#             else:
#                 recipe = result.data
#                 logger.info(f"Recipe found: {recipe.recipe_name}")
#                 print(f"Recipe found: {recipe.recipe_name}")
#                 print(f"Ingredients: {', '.join(recipe.ingredients)}")
#                 print("Steps:")
#                 for idx, (step, time) in enumerate(zip(recipe.steps, recipe.step_times)):
#                     print(f"{idx+1}. {step} (Time: {time})")
                
#                 # Ask user to finalize or generate another recipe
#                 answer = input("Do you want to finalize this recipe or generate another? (finalize/generate): ")
#                 if answer.lower() == 'finalize':
#                     logger.info(f"Recipe finalized: {recipe.recipe_name}")
#                     break
#         except Exception as e:
#             logger.error(f"Error generating recipe: {e}")
#             print("Error generating recipe, please try again.")

# if __name__ == '__main__':
#     import asyncio
#     asyncio.run(main())