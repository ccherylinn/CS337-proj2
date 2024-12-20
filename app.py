from slack_bolt import App
from dotenv import load_dotenv
from directions import fetch_recipe_page 
from directions import get_temperature_api
from datafetch import parse_recipe
from parserhelper import find_ingredients_in_string
from parserhelper import answer_cooking_question
import os
import string
import re

load_dotenv()
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

user_sessions = {}    

def get_step(user_id, delta):
    if user_sessions.get(user_id, {}).get("last_action") == "recipe_selected":
        user_sessions[user_id]["current_step"] += delta
        steps = user_sessions[user_id].get("steps", [])
        step_number = 'Step ' + str(user_sessions.get(user_id)["current_step"])

        if step_number in steps:
            return f"{step_number}: {steps[step_number]}"
        else:
            user_sessions[user_id]["current_step"] -= delta
            return "No more steps."
    else:
        return "Please provide a AllRecipes URL first."

@app.event("message")
def handle_dm_messages(event, say):
    if event.get("channel_type") == "im":
        user_id = event.get("user")
        user_message = str(event.get("text")).lower()

        if "allrecipes.com" in user_message:
            url = user_message.strip('<>')
            say(text="Fetching recipe...")
            html_content = fetch_recipe_page(url)
            parsed_recipe = parse_recipe(html_content)

            user_sessions[user_id] = {
                "ingredients": parsed_recipe['ingredients'],
                "tools": parsed_recipe['tools'],
                "steps": parsed_recipe['directions'],
                "methods": parsed_recipe['methods'],
                "current_step": 0,
                "last_action": "recipe_selected"
            }

            say(text="Recipe loaded. What would you like to do?")
            say(text="* List ingredients")
            say(text="* List tools")
            say(text="* List cooking methods")
            say(text="* Go over recipe steps")
        
        elif "ingredients" in user_message:
            if user_sessions.get(user_id, {}).get("last_action") == "recipe_selected":
                if "descriptor" in user_message:
                    ingredients = user_sessions[user_id].get("ingredients", [])

                    formatted_ingredients = [f"{item['amount']} {item['unit']} {item['name']}, descriptor is: {item['descriptor']}" for item in ingredients]

                    say(text="Here are the ingredients:\n" + "\n".join(formatted_ingredients))
                elif "preparation" in user_message:
                    ingredients = user_sessions[user_id].get("ingredients", [])

                    formatted_ingredients = [f"{item['amount']} {item['unit']} {item['name']}, preparation is: {item['preparation']}" for item in ingredients]

                    say(text="Here are the ingredients:\n" + "\n".join(formatted_ingredients))
                else:
                    ingredients = user_sessions[user_id].get("ingredients", [])

                    formatted_ingredients = [f"{item['amount']} {item['unit']} {item['name']}" for item in ingredients]

                    say(text="Here are the ingredients:\n" + "\n".join(formatted_ingredients))
            else:
                say(text="Please provide an AllRecipes URL first.")
            
        elif "tools" in user_message:
            if user_sessions.get(user_id, {}).get("last_action") == "recipe_selected":
                tools = user_sessions[user_id].get("tools", [])
                say(text="Here are the tools:\n" + "\n".join(tools))
            else:
                say(text="Please provide an AllRecipes URL first.")
        
        elif "methods" in user_message:
            if user_sessions.get(user_id, {}).get("last_action") == "recipe_selected":
                primary_methods = user_sessions[user_id].get("methods", {})[0]
                secondary_methods = user_sessions[user_id].get("methods", {})[1]
                say(text="Here are the methods:\n" + ", ".join(primary_methods))
                say(text="Here are the secondary methods:\n" + ", ".join(secondary_methods)) 
            else:
                say(text="Please provide an AllRecipes URL first.")

        elif "list" in user_message and "steps" in user_message:
            if user_sessions.get(user_id, {}).get("last_action") == "recipe_selected":
                steps = user_sessions[user_id].get("steps", [])
                for step, value in steps.items():
                    say(f"{step}: {value}")
            else:
                say(text="Please provide an AllRecipes URL first.")

        elif "start" in user_message and "step" in user_message:
            say(text=get_step(user_id, 1))

        elif "next" in user_message and "step" in user_message:
            say(text=get_step(user_id, 1))

        elif "repeat" in user_message and "step" in user_message:
            say(text=get_step(user_id, 0))

        elif ("previous" in user_message or "back" in user_message) and "step" in user_message:
            say(text=get_step(user_id, -1))

        elif " to step " in user_message:
            no_punctuation = user_message.translate(str.maketrans('', '', string.punctuation)).strip()
            step = int(no_punctuation.split()[-1])
            if user_sessions.get(user_id, {}).get("last_action") == "recipe_selected":
                steps = user_sessions[user_id].get("steps", [])
                step_number = 'Step ' + str(step)

                if step_number in steps:
                    user_sessions[user_id]["current_step"] = step
                    say(text=f"{step_number}: {steps[step_number]}")
                else:
                    say(text=step_number + " does not exist.")
            else:
                say(text="Please provide an AllRecipes URL first.")
            
        elif "temperature" in user_message:
            if user_sessions.get(user_id, {}).get("last_action") == "recipe_selected":
                current_step = user_sessions.get(user_id)['steps']['Step ' + str(user_sessions.get(user_id)["current_step"])]
                say(text=', '.join(get_temperature_api(current_step)))
            else:
                say(text="Please provide an AllRecipes URL first.")
            
        elif "how long do i" in user_message or "done" in user_message:
            if user_sessions.get(user_id, {}).get("last_action") == "recipe_selected":
                current_step = user_sessions.get(user_id)['steps']['Step ' + str(user_sessions.get(user_id)["current_step"])]
                say(text=answer_cooking_question(current_step, user_message))
            else:
                say(text="Please provide an AllRecipes URL first.")
        
        elif "how much" in user_message:
            if user_sessions.get(user_id, {}).get("last_action") == "recipe_selected":
                pattern = r"how much\s+(.*?)(?:\s+(do|should|is)|$)"
                match = re.search(pattern, user_message, re.IGNORECASE)
                if match:
                    ingr_text = match.group(1)
                    for ingredient in user_sessions.get(user_id)['ingredients']:
                        if ingr_text in ingredient["name"]:
                            amt = ingredient['amount']
                            unit = ingredient['unit']
                            # ingredient_name = ingredient['name']
                    #         say(text=f"You need: {amt} {unit} of {ingredient_name} for the whole recipe.")
                    current_step = user_sessions.get(user_id)['steps']['Step ' + str(user_sessions.get(user_id)["current_step"])]
                    for part in current_step.split(','):
                        if ingr_text in part:
                            search_text = part.split(ingr_text)[0].split()
                            isDigit = False
                            i = len(search_text) - 1

                            while i >= 0:
                                if all(char.isdigit() or char in string.punctuation for char in search_text[i]):
                                    isDigit = True
                                    break
                                else:
                                    i -= 1

                            if not isDigit:
                                say(text=f"You need: {amt} {unit} of {ingr_text} for this step.")
                            else:
                                unit2 = search_text[i + 1]
                                amount = search_text[i]
                                if i - 1 >= 0 and search_text[i-1].isdigit():
                                    amount = search_text[i-1] + " " + search_text[i]
                                say(text=f"You need: {amount} {unit2} of {ingr_text} for this step.")
                    if ingr_text not in current_step:
                        say(text=f"{ingr_text} not used in this step")
                else:
                    say(text="Unrecognized command.")
            else:
                say(text="Please provide an AllRecipes URL first.")

        elif "how do i do that" in user_message or "how do you do that" in user_message:
            if user_sessions.get(user_id, {}).get("last_action") == "recipe_selected":
                current_step = user_sessions.get(user_id)['steps']['Step ' + str(user_sessions.get(user_id)["current_step"])]
                no_punctuation = current_step.translate(str.maketrans('', '', string.punctuation)).split()

                ingredients = find_ingredients_in_string(user_sessions.get(user_id)['ingredients'], current_step)
                if not ingredients:
                    say(text="Google Search: https://www.google.com/search?q=how+to+"+'+'.join(no_punctuation))
                else:
                    filtered_words = []
                    i = 0
                    while i < len(no_punctuation):
                        if no_punctuation[i].isdigit():
                            while i < len(no_punctuation) and no_punctuation[i].isdigit():
                                i += 1
                            i += 1
                        else:
                            filtered_words.append(no_punctuation[i])
                            i += 1
                    say(text="Google Search: https://www.google.com/search?q=how+to+"+'+'.join(filtered_words))
            else:
                say(text="Please provide an AllRecipes URL first.")
            
        elif "instead" in user_message:
            if user_sessions.get(user_id, {}).get("last_action") == "recipe_selected":
                pattern = r"instead of\s+(.*?)(?:\s+to|[?.!,]|$)"
                match = re.search(pattern, user_message, re.IGNORECASE)
                if match:
                    item = match.group(1)
                    current_step = user_sessions.get(user_id)['steps'][f"Step {user_sessions.get(user_id)['current_step']}"]
                    if item not in current_step:
                        say(text=f"{item} not used in current step.")
                    else:
                        say(text=f"Google Search: https://www.google.com/search?q={'+'.join(user_message.split())}")
                else:
                    say(text="Unrecognized command.")
            else:
                say(text="Please provide an AllRecipes URL first.")

        elif user_message.startswith("what is") or user_message.startswith("how to") or user_message.startswith("how do i") or user_message.startswith("how do you"):
            if user_sessions.get(user_id, {}).get("last_action") == "recipe_selected":
                say(text="Google Search: https://www.google.com/search?q="+'+'.join(user_message.split()))
            else:
                say(text="Please provide an AllRecipes URL first.")

        elif user_message == "cs337" or user_message == "nlp":
            say(text="hi larry and simon :D")
        
        else:
            if user_id not in user_sessions:
                say(text="Please specify an AllRecipes URL.")
            else:
                say(text="Unrecognized command.")

if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
