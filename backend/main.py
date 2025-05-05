import os
import re
import json
import pymongo
from pymongo.server_api import ServerApi
import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import google.generativeai as genai
import traceback
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("ERROR: GOOGLE_API_KEY environment variable not set. Did you create a .env file and set the variable?")
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        print("Gemini API Key configured successfully from environment variable.")
    except Exception as e:
        print(f"ERROR: Failed to configure Gemini API Key: {e}")
        GOOGLE_API_KEY = None

MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_USER = os.getenv("MONGO_USER")
MONGO_CLUSTER_URL = os.getenv("MONGO_CLUSTER_URL")

mongo_client = None
db = None
orders_collection = None

if not MONGO_PASSWORD:
    print("ERROR: MONGO_PASSWORD environment variable not set. Did you create a .env file and set the variable?")
else:
    MONGO_URI = f"mongodb+srv://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_CLUSTER_URL}/?retryWrites=true&w=majority&appName=UserOrders"
    try:
        mongo_client = pymongo.MongoClient(MONGO_URI, server_api=ServerApi('1'))
        mongo_client.admin.command('ping')
        print("Successfully connected to MongoDB using credentials from environment variables!")
        db = mongo_client["mcdonalds_orders"]
        orders_collection = db["orders"]
    except Exception as e:
        print(f"ERROR: Could not connect to MongoDB: {e}")
        traceback.print_exc()
        mongo_client = None
        db = None
        orders_collection = None

mcdonalds_menu = {
    "big mac": {"price": 5.99, "description": "Two all-beef patties, special sauce, lettuce, cheese, pickles, onions on a sesame seed bun."},
    "quarter pounder with cheese": {"price": 6.19, "description": "Quarter pound 100% fresh beef patty, cheese, ketchup, mustard, pickles, onions."},
    "double quarter pounder with cheese": {"price": 8.29, "description": "Two quarter pound 100% fresh beef patties, cheese, ketchup, mustard, pickles, onions."},
    "mcdouble": {"price": 3.49, "description": "Two 100% beef patties, cheese, ketchup, mustard, pickles, onions."},
    "cheeseburger": {"price": 2.79, "description": "100% beef patty, cheese, ketchup, mustard, pickle, onions."},
    "hamburger": {"price": 2.49, "description": "100% beef patty, ketchup, mustard, pickle, onions."},
    "mcchicken": {"price": 3.19, "description": "Crispy chicken patty, lettuce, mayonnaise."},
    "filet-o-fish": {"price": 5.69, "description": "Fish filet patty, tartar sauce, half slice of cheese."},
    "4 piece chicken mcnuggets": {"price": 3.29, "description": "4 piece Chicken McNuggets with choice of sauce."},
    "6 piece chicken mcnuggets": {"price": 4.49, "description": "6 piece Chicken McNuggets with choice of sauce."},
    "10 piece chicken mcnuggets": {"price": 5.99, "description": "10 piece Chicken McNuggets with choice of sauce."},
    "20 piece chicken mcnuggets": {"price": 8.99, "description": "20 piece Chicken McNuggets with choice of sauce."},
    "small fries": {"price": 2.59, "description": "Small World Famous Fries."},
    "medium fries": {"price": 3.39, "description": "Medium World Famous Fries."},
    "large fries": {"price": 3.99, "description": "Large World Famous Fries."},
    "small coke": {"price": 1.89, "description": "Small Coca-Cola."},
    "medium coke": {"price": 2.19, "description": "Medium Coca-Cola."},
    "large coke": {"price": 2.59, "description": "Large Coca-Cola."},
    "small sprite": {"price": 1.89, "description": "Small Sprite."},
    "medium sprite": {"price": 2.19, "description": "Medium Sprite."},
    "large sprite": {"price": 2.59, "description": "Large Sprite."},
    "small diet coke": {"price": 1.89, "description": "Small Diet Coke."},
    "medium diet coke": {"price": 2.19, "description": "Medium Diet Coke."},
    "large diet coke": {"price": 2.59, "description": "Large Diet Coke."},
    "small dr pepper": {"price": 1.89, "description": "Small Dr Pepper."},
    "medium dr pepper": {"price": 2.19, "description": "Medium Dr Pepper."},
    "large dr pepper": {"price": 2.59, "description": "Large Dr Pepper."},
    "small fanta": {"price": 1.89, "description": "Small Fanta Orange."},
    "medium fanta": {"price": 2.19, "description": "Medium Fanta Orange."},
    "large fanta": {"price": 2.59, "description": "Large Fanta Orange."},
    "small orange hi-c": {"price": 1.89, "description": "Small Orange Hi-C."},
    "medium orange hi-c": {"price": 2.19, "description": "Medium Orange Hi-C."},
    "large orange hi-c": {"price": 2.59, "description": "Large Orange Hi-C."},
    "bottled water": {"price": 1.89, "description": "Dasani Bottled Water."},
    "mcflurry with oreo cookies": {"price": 4.19, "description": "Vanilla soft serve swirled with OREO cookies."},
    "mcflurry with m&ms": {"price": 4.19, "description": "Vanilla soft serve swirled with M&M'S chocolate candies."},
    "baked apple pie": {"price": 1.99, "description": "Hot baked apple pie."},
    "chocolate chip cookie": {"price": 1.29, "description": "Single warm chocolate chip cookie."},
    "honey mustard sauce": {"price": 0.25, "description": "Honey Mustard Sauce Packet."},
    "tangy barbeque sauce": {"price": 0.25, "description": "Tangy Barbeque Sauce Packet."},
    "spicy buffalo ranch sauce": {"price": 0.25, "description": "Spicy Buffalo Ranch Sauce Packet."},
    "creamy ranch sauce": {"price": 0.25, "description": "Creamy Ranch Sauce Packet."},
    "ketchup packet": {"price": 0.25, "description": "Ketchup Packet."},
    "mayonnaise packet": {"price": 0.25, "description": "Mayonnaise Packet."},
    "tartar sauce packet": {"price": 0.25, "description": "Tartar Sauce Packet."},
}

def format_menu_for_prompt(menu: Dict) -> str:
    menu_str = "Available Menu Items:\n"
    for name, details in menu.items():
        try:
            price = float(details.get('price', 0.0))
            menu_str += f"- {name.title()}: ${price:.2f} ({details.get('description', '')})\n"
        except (ValueError, TypeError):
             menu_str += f"- {name.title()}: (Price Error) ({details.get('description', '')})\n"
    return menu_str

def format_context_for_prompt(order_context: Optional['OrderContext']) -> str:
    if not order_context or not order_context.items:
        return "The user's order is currently empty."
    else:
        try:
            if isinstance(order_context, OrderContext):
                 context_dict = order_context.model_dump(exclude={'is_finalized'})
            else:
                 temp_context = OrderContext(**order_context)
                 context_dict = temp_context.model_dump(exclude={'is_finalized'})
            if not context_dict.get("items"):
                 return "The user's order is currently empty."
            return f"Current Order State (JSON):\n```json\n{json.dumps(context_dict, indent=2)}\n```"
        except Exception as e:
            print(f"Error dumping model context for prompt: {e}")
            return "Error formatting current order state. Assume order is empty."

class OrderItemDetail(BaseModel):
    quantity: int = Field(gt=0)
    base_price: float = Field(ge=0)
    total_price: float = Field(ge=0)
    modifications: List[str] = Field(default_factory=list)

class OrderContext(BaseModel):
    items: Dict[str, OrderItemDetail] = Field(default_factory=dict)
    subtotal: float = Field(default=0.0, ge=0)
    is_finalized: bool = False

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    reply: str
    context: OrderContext

SYSTEM_PROMPT_TEMPLATE = """
You are "McBot", a friendly and helpful AI assistant for taking McDonald's orders.
Your goal is to assist users in building their order, handling requests naturally, and keeping track of the items, modifications, quantities, and subtotal accurately.

**Your Instructions:**

1.  **Be Conversational:** Respond politely and naturally. Understand greetings and respond appropriately. Always ask "Anything else?" after successfully adding or modifying an item, unless the order is being finalized (see rule 11).

2.  **Use the Menu:** Only add items from the menu provided below. If a user asks for something not on the menu, politely inform them it's unavailable. Prices are listed in the menu. Use the exact item names from the menu as keys in the JSON `items` dictionary (e.g., "large fries", "honey mustard sauce").

3.  **Track the Order:** Maintain a list of items the user has added in the `items` dictionary within the JSON context. Each item key should be the exact item name from the menu. The value should be an object containing `quantity`, `base_price` (from the menu), `total_price` (quantity * base_price), and a list of `modifications`. If a user orders an item already in the list, increment the `quantity` and update the `total_price`.

4.  **Handle Multiple Items & Details:** If the user mentions multiple items or details in a single message (e.g., "filet o fish and large fries", "2 mcchickens and a small coke"), add all recognized items with their specified details. **Crucially, capture associated details like size or quantity mentioned for each item (e.g., if the user says 'large fries', add 'large fries', not just 'fries'; if they say '2 ketchup packets', set quantity to 2).** If a size or essential detail is truly missing for an item that requires it (like fries or drinks), then ask for clarification *only for that specific item*, while still adding any other fully specified items from the message.
    * Example 1 (Size Provided): User: 'a mcchicken and a large sprite' -> Bot adds 'mcchicken' (qty 1) and 'large sprite' (qty 1) to the JSON, then asks 'Anything else?'
    * Example 2 (Size Missing): User: 'fillet o fish and fries' -> Bot adds 'filet-o-fish' (qty 1) to JSON. Recognizes 'fries' but size is missing. Bot asks 'I've added the Filet-o-Fish. What size fries would you like?' (The Filet-o-Fish remains in the JSON context).

5.  **Handle Modifications:** Understand requests like "extra cheese", "no pickles", "add onions", "plain". Add these modifications as strings to the `modifications` list for the specific item in the `items` dictionary. Assume simple modifications do not change the `base_price`.

6.  **Calculate Subtotal:** Keep a running `subtotal` of all items in the order. **Update it accurately** whenever items are added, removed, or quantities change. The subtotal MUST be the sum of the `total_price` for every item currently in the `items` dictionary. Calculate prices carefully (quantity * base_price).

7.  **Show Menu/Order/Subtotal:** If the user asks for the "menu", their "order", or "subtotal", provide that information clearly based on the current context JSON. Format the order details nicely in your reply.

8.  **Handle Ambiguity:** If the user's request is unclear (e.g., "add a burger"), ask for clarification (e.g., "Which burger would you like? We have...").

9.  **Handle Removal/Quantity Change:** Understand requests like "remove the big mac", "take off the fries", "make that 2 cokes instead of 1", "I only want one fries". Update the `items` dictionary (remove item or change quantity) and recalculate the `subtotal` correctly.

10. **Handle Off-Topic:** If the user asks something unrelated to ordering, gently redirect them back to the order. Example: "I can only help with McDonald's orders right now. Was there anything else you wanted to add?"

11. **Finalize Order:** When the user clearly indicates they are finished ordering (e.g., says 'no', 'that's all', 'nope', 'that's it' in response to 'Anything else?'), **do not ask 'Anything else?' again.** Instead, follow these steps meticulously:
    * **First, summarize the order:** In your text reply, list the quantity and name of each item currently in the `items` dictionary (based on the final state you are about to put in the JSON). Format it naturally (e.g., "Okay, so you have 1 Filet-O-Fish, 1 Large Fries, and 2 Honey Mustard Sauce."). Include any modifications if present.
    * **Then, state the final subtotal:** Clearly state the final total based on the `subtotal` field calculated for the JSON context.
    * **Finally, provide a polite closing message.** (e.g., "Thanks for ordering with McBot!")
    * **CRITICAL JSON Step:** In the JSON block accompanying this final reply, set the field `"is_finalized": true`. **The `items` dictionary and `subtotal` in this final JSON MUST perfectly match all the items, quantities, modifications, and the total price stated in your textual summary.** Ensure all calculations are correct.

12. **Output Format:** Your response MUST contain two parts:
    * The user-facing conversational reply based on the instructions above.
    * A JSON block representing the COMPLETE updated order state, enclosed in ```json ... ```. This JSON block MUST strictly follow the structure of the `OrderContext` model (containing `items`, `subtotal`, and `is_finalized`). Double-check your JSON structure, item names, quantities, prices, modifications, and the subtotal for accuracy before outputting. Set `is_finalized` to `true` ONLY when finalizing the order as per rule 11.

**Menu:**
{menu_string}

**Current Order State:**
{context_string}

**User Message:**
{user_message}

**Your Response (Reply + JSON):** Ensure the JSON is valid and accurately reflects the order state described in the reply.  
"""

@app.post("/api/chat", response_model=ChatResponse)
async def chat_handler(request: ChatRequest):
    print(f"Received request: message='{request.message}', context={request.context}")
    user_message = request.message

    current_context = OrderContext()
    if request.context:
        try:
            current_context = OrderContext(**request.context)
            current_context.is_finalized = False
            print("Successfully parsed incoming context.")
        except Exception as e:
             print(f"Warning: Could not parse incoming context dict: {e}. Using empty context.")

    if not GOOGLE_API_KEY:
        print("ERROR in chat_handler: Google API key is missing or failed to configure.")
        raise HTTPException(status_code=500, detail="API key is not configured correctly on the server.")

    menu_str = format_menu_for_prompt(mcdonalds_menu)
    context_str = format_context_for_prompt(current_context)

    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        menu_string=menu_str,
        context_string=context_str,
        user_message=user_message
    )

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("Calling Gemini API...")
        llm_response = await model.generate_content_async(prompt)
        print("Received response from Gemini.")

        llm_response_text = ""
        try:
            if hasattr(llm_response, 'text'):
                llm_response_text = llm_response.text
            elif hasattr(llm_response, 'parts') and llm_response.parts:
                 llm_response_text = "".join(part.text for part in llm_response.parts if hasattr(part, 'text'))
            else:
                 if hasattr(llm_response, 'prompt_feedback') and llm_response.prompt_feedback and llm_response.prompt_feedback.block_reason:
                      block_reason = llm_response.prompt_feedback.block_reason
                      block_message = llm_response.prompt_feedback.block_reason_message or "Blocked by safety filter."
                      print(f"Warning: LLM Response Blocked. Reason: {block_reason}")
                      raise HTTPException(status_code=400, detail=f"Request blocked by AI safety filter: {block_message}")
                 else:
                     print(f"Warning: Unexpected LLM response structure: {llm_response}")
                     llm_response_text = str(llm_response)

            if not llm_response_text.strip():
                 print("Warning: LLM response text is empty.")
                 if hasattr(llm_response, 'prompt_feedback') and llm_response.prompt_feedback and llm_response.prompt_feedback.block_reason:
                      block_reason = llm_response.prompt_feedback.block_reason
                      block_message = llm_response.prompt_feedback.block_reason_message or "Blocked by safety filter."
                      print(f"Warning: LLM Response Blocked (empty text). Reason: {block_reason}")
                      raise HTTPException(status_code=400, detail=f"Request blocked by AI safety filter (empty response): {block_message}")
                 raise ValueError("LLM returned an empty response text.")

        except HTTPException as http_exc:
             raise http_exc
        except Exception as e:
            print(f"Error accessing LLM response content: {e}")
            print(f"Raw LLM response object: {llm_response}")
            raise HTTPException(status_code=500, detail=f"Error processing response from AI model: {e}")

        print(f"LLM Raw Response Text:\n{llm_response_text}\n--------------------")

        reply_text = llm_response_text
        updated_context = current_context

        json_match = re.search(r"```json\s*({.*?})\s*```", llm_response_text, re.DOTALL)
        updated_context_dict = None
        validation_error = False
        validation_error_message = "Failed to process order update."

        if json_match:
            json_string_found = json_match.group(1)
            try:
                updated_context_dict = json.loads(json_string_found)
                print("Successfully parsed JSON from LLM response.")
                validated_context = OrderContext(**updated_context_dict)
                calculated_subtotal = sum(item.total_price for item in validated_context.items.values())
                if abs(validated_context.subtotal - calculated_subtotal) > 0.01:
                    print(f"Warning: LLM subtotal ({validated_context.subtotal}) differs from calculated subtotal ({calculated_subtotal}). Using calculated value.")
                    validated_context.subtotal = calculated_subtotal
                updated_context = validated_context
                print("Context dictionary validated successfully.")
                reply_text = re.sub(r"```json\s*({.*?})\s*```", "", llm_response_text, flags=re.DOTALL).strip()
                if not reply_text: reply_text = "Okay, order updated."

            except json.JSONDecodeError as e:
                print(f"ERROR: Failed to decode JSON from LLM response: {e}\nJSON String Attempted: {json_string_found}")
                validation_error = True
                validation_error_message = f"Internal error: AI returned improperly formatted order data (JSON Decode Error: {e})."
            except Exception as e:
                print(f"ERROR: Error validating LLM context JSON: {e}\nDict Attempted: {updated_context_dict}")
                validation_error = True
                validation_error_message = f"Internal error: AI returned invalid order data (Validation Error: {e})."
        else:
             print("Warning: No JSON block found in LLM response.")
             validation_error = True
             validation_error_message = "Sorry, I couldn't update the order state. Please try rephrasing your request."

        if validation_error:
            print(f"Warning: Could not parse or validate updated context JSON. Falling back to previous context.")
            return ChatResponse(
                reply=f"{validation_error_message}\n(Your previous order state is maintained.)",
                context=current_context
            )

        if updated_context.is_finalized:
            print("Order finalized. Attempting to save to MongoDB...")
            if orders_collection is not None and mongo_client is not None:
                try:
                    order_data = updated_context.model_dump()
                    order_data['orderTimestamp'] = datetime.datetime.now(datetime.timezone.utc)
                    insert_result = orders_collection.insert_one(order_data)
                    print(f"Order successfully saved to MongoDB with ID: {insert_result.inserted_id}")
                except Exception as e:
                    print(f"ERROR: Failed to save finalized order to MongoDB: {e}")
                    traceback.print_exc()
                    reply_text += " (Note: There was an issue saving the order to the database.)"
            else:
                 print("Warning: MongoDB connection not available. Cannot save finalized order.")
                 reply_text += " (Note: Order could not be saved to database due to connection issue.)"

        print(f"Sending response: reply='{reply_text}', context={updated_context.model_dump()}")
        return ChatResponse(reply=reply_text, context=updated_context)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"FATAL ERROR in chat_handler: {e}")
        traceback.print_exc()
        fallback_context = current_context
        error_reply = "Sorry, an unexpected server error occurred. Please try again later."
        return ChatResponse(reply=error_reply, context=fallback_context)

if __name__ == "__main__":
    import uvicorn
    print("Starting McBot server...")
    if not GOOGLE_API_KEY:
         print("!!! FATAL: GOOGLE_API_KEY not found in environment variables. Server cannot start. !!!")
         exit()
    if not orders_collection:
        print("!!! WARNING: MongoDB connection failed or not established during startup. Orders cannot be saved. !!!")
    else:
        print("MongoDB connection appears successful.")

    print("Server attempting to start...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)