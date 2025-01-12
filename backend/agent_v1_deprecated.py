#Does not work

# import openai
# import sys
# import pandas as pd
# import os
# from pydantic_ai import Agent, RunContext
# from dotenv import load_dotenv

# # Load environment variables from .env
# load_dotenv()

# # Set OpenAI API key
# openai.api_key = os.getenv("OPENAI_API_KEY")

# # Define the agent
# recipe_agent = Agent(
#     'openai:gpt-4o-mini',
#     deps_type=dict,  # Dependencies will include available ingredients
#     result_type=str,  # Result will be the recipe as a string
#     system_prompt=(
#         'You are an AI chef. You can use the `generate_recipe` function to create recipes '
#         'based on dietary preferences, cuisine type, and available ingredients.'
#     ),
# )

# # Define a tool for generating recipes
# @recipe_agent.tool
# async def generate_recipe(ctx: RunContext[dict]) -> str:
#     """
#     Create a recipe based on dietary preferences, cuisine type, and available ingredients.
#     """
#     # Extract dependencies and user inputs from context
#     diet = ctx.deps.get("diet", "any")
#     cuisine = ctx.deps.get("cuisine", "any")
#     specific_ingredients = ctx.deps.get("specific_ingredients", [])
#     available_ingredients = ctx.deps.get("available_ingredients", [])

#     prompt = f"""
#     Create a {diet} recipe with a {cuisine} twist.
#     Specific ingredients requested: {', '.join(specific_ingredients)}.
#     Available ingredients: {', '.join(available_ingredients)}.
#     Provide step-by-step instructions in detail.
#     """

#     # # Use OpenAI's GPT to generate the recipe
#     # response = openai.Completion.create(
#     #     engine="text-davinci-003",
#     #     prompt=prompt,
#     #     max_tokens=500
#     # )
#     # return response.choices[0].text.strip()
    
#     response = openai.chat.completions.create(
#         model="gpt-4o-mini",  # Use the appropriate model (gpt-4 or gpt-3.5-turbo)
#         messages=[
#             {"role": "system", "content": "You are an AI chef."},
#             {"role": "user", "content": prompt}
#         ],
#         max_tokens=500
#     )
    
#     print(response["choices"][0])

#     response_content = response['choices'][0]['message']['content']
#     return response_content

# # Function to read ingredients from Excel
# def get_available_ingredients(file_path):
#     df = pd.read_excel(file_path)
#     return df['Ingredient'].dropna().tolist()

# def main():
#     # Fetch arguments passed from Node.js backend
#     diet = sys.argv[1]
#     cuisine = sys.argv[2]
#     specific_ingredients = sys.argv[3].split(",")  # Convert comma-separated string into a list

#     # Load available ingredients from Excel
#     excel_path = "ingredients.xlsx"  # Path to the Excel file
#     available_ingredients = get_available_ingredients(excel_path)

#     # Prepare user inputs
#     user_inputs = {
#         "diet": diet,
#         "cuisine": cuisine,
#         "specific_ingredients": specific_ingredients
#     }

#     # Run the agent
#     result = recipe_agent.run_sync(
#         "Generate a recipe", 
#         deps={"available_ingredients": available_ingredients, "diet": diet, "cuisine": cuisine, "specific_ingredients": specific_ingredients}
#     )

#     # Print the result which can be captured by Node.js
#     print(result.data)

# if __name__ == "__main__":
#     main()
