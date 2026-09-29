import json
import time

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import render

from google import genai
from google.genai import types

from apps.ai_agent.tools import (
    get_delivery_summary,
    update_delivery_status,
)


# =========================
# Gemini Client
# =========================

client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)


# =========================
# Gemini Tool Definitions
# =========================

delivery_summary_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_delivery_summary",
            description=(
                "Get delivery statistics including total, "
                "pending, assigned, picked up, in transit, "
                "delivered, and active deliveries."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={},
            ),
        )
    ]
)


update_delivery_status_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="update_delivery_status",
            description=(
                "Update the status of a delivery. "
                "Use this only when the user clearly asks "
                "to change a delivery status."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "delivery_id": types.Schema(
                        type="INTEGER",
                        description="The delivery ID."
                    ),
                    "new_status": types.Schema(
                        type="STRING",
                        description=(
                            "New delivery status. "
                            "Allowed values: pending, assigned, "
                            "picked_up, in_transit, delivered."
                        )
                    ),
                    "note": types.Schema(
                        type="STRING",
                        description="Optional note about the status change."
                    ),
                },
                required=[
                    "delivery_id",
                    "new_status",
                ],
            ),
        )
    ]
)


# =========================
# AI Context
# =========================

def parse_ai_context(request):
    raw_context = request.POST.get(
        "context",
        ""
    ).strip()

    if not raw_context:
        return {}

    try:
        context = json.loads(raw_context)

    except (
        json.JSONDecodeError,
        TypeError,
    ):
        return {}

    if not isinstance(context, dict):
        return {}

    return context


def build_context_text(request, context):
    user = request.user

    safe_context = {
        "current_page": context.get(
            "page",
            "/ai/"
        ),
        "page_name": context.get(
            "page_name",
            "AI Assistant"
        ),
        "user_role": user.effective_role,
    }

    dashboard_stats = context.get(
        "dashboard_stats"
    )

    if isinstance(
        dashboard_stats,
        dict
    ):
        safe_context["dashboard_stats"] = (
            dashboard_stats
        )

    status_filter = context.get(
        "delivery_status_filter"
    )

    if isinstance(
        status_filter,
        str
    ):
        safe_context[
            "delivery_status_filter"
        ] = status_filter[:50]

    delivery_search = context.get(
        "delivery_search"
    )

    if isinstance(
        delivery_search,
        str
    ):
        safe_context[
            "delivery_search"
        ] = delivery_search[:100]

    return json.dumps(
        safe_context,
        ensure_ascii=False
    )


# =========================
# Error Handling
# =========================

def get_user_friendly_error(error):

    if isinstance(
        error,
        PermissionDenied
    ):
        return (
            "You do not have permission "
            "to perform this action."
        )

    if isinstance(
        error,
        ValueError
    ):
        return str(error)

    error_text = str(
        error
    ).lower()

    if (
        "api key" in error_text
        or "authentication" in error_text
    ):
        return (
            "The AI service is not configured "
            "correctly. Please contact the administrator."
        )

    if (
        "503" in error_text
        or "unavailable" in error_text
        or "service unavailable" in error_text
    ):
        return (
            "The AI service is temporarily unavailable. "
            "Please try again in a moment."
        )

    if (
        "timeout" in error_text
        or "timed out" in error_text
    ):
        return (
            "The AI service took too long to respond. "
            "Please try again."
        )

    return (
        "Something went wrong while processing "
        "your request. Please try again."
    )


# =========================
# Gemini Request
# =========================

def generate_ai_response(
    user_message,
    context_text,
    user,
):

    system_instruction = f"""
You are Smart Delivery AI Assistant.

You are an AI assistant embedded inside
a Django delivery management system.

You must help the authenticated user
with delivery and logistics operations.

Current application context:
{context_text}

Important rules:

1. Respect the authenticated user's role.
2. Never claim that an action was completed
   unless the backend tool actually completed it.
3. Use tools when real application data
   is required.
4. Do not invent delivery or driver data.
5. Keep responses concise and clear.
6. If a tool returns an error, explain it
   clearly to the user.
7. For status updates, use the backend tool.
8. Never bypass backend permissions.
"""

    tools = [
        delivery_summary_tool,
        update_delivery_status_tool,
    ]

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=tools,
            temperature=0.2,
        ),
    )

    return response


# =========================
# AI Assistant View
# =========================

@login_required
def ai_assistant(request):

    if request.method == "GET":
        return render(
            request,
            "ai/ai.html"
        )

    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "reply": "Invalid request method.",
            },
            status=405,
        )

    try:

        user_message = request.POST.get(
            "message",
            ""
        ).strip()

        if not user_message:
            return JsonResponse(
                {
                    "success": False,
                    "reply": "Please enter a message.",
                },
                status=400,
            )

        context = parse_ai_context(
            request
        )

        context_text = build_context_text(
            request,
            context
        )

        print(
            "AI CONTEXT:",
            context_text,
            flush=True,
        )

        # =========================
        # First Gemini Request
        # =========================

        response = generate_ai_response(
            user_message,
            context_text,
            request.user,
        )

        # =========================
        # Tool Calling Loop
        # =========================

        max_tool_calls = 3
        tool_call_count = 0

        while (
            response.function_calls
            and tool_call_count < max_tool_calls
        ):

            tool_call_count += 1

            tool_responses = []

            for function_call in (
                response.function_calls
            ):

                function_name = (
                    function_call.name
                )

                function_args = (
                    function_call.args or {}
                )

                print(
                    "AI TOOL:",
                    function_name,
                    function_args,
                    flush=True,
                )

                # =========================
                # Delivery Summary
                # =========================

                if function_name == (
                    "get_delivery_summary"
                ):

                    tool_result = (
                        get_delivery_summary(
                            request.user
                        )
                    )

                # =========================
                # Update Delivery Status
                # =========================

                elif function_name == (
                    "update_delivery_status"
                ):

                    delivery_id = (
                        function_args.get(
                            "delivery_id"
                        )
                    )

                    new_status = (
                        function_args.get(
                            "new_status"
                        )
                    )

                    note = (
                        function_args.get(
                            "note",
                            ""
                        )
                    )

                    tool_result = (
                        update_delivery_status(
                            user=request.user,
                            delivery_id=delivery_id,
                            new_status=new_status,
                            note=note,
                        )
                    )

                else:

                    raise ValueError(
                        f"Unknown AI tool: "
                        f"{function_name}"
                    )

                print(
                    "Tool Result:",
                    tool_result,
                    flush=True,
                )

                tool_responses.append(
                    types.Part.from_function_response(
                        name=function_name,
                        response={
                            "result": tool_result
                        },
                    )
                )

            # =========================
            # Send Tool Results to Gemini
            # =========================

            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[
                    user_message,
                    *tool_responses,
                ],
                config=types.GenerateContentConfig(
                    system_instruction=(
                        f"""
You are Smart Delivery AI Assistant.

Application context:
{context_text}

Use the tool results to answer the
authenticated user.

Do not invent information.

If a tool reports an error,
clearly explain that error.

Only say that an action was completed
when the tool result confirms success.
"""
                    ),
                    tools=[
                        delivery_summary_tool,
                        update_delivery_status_tool,
                    ],
                    temperature=0.2,
                ),
            )

        # =========================
        # Final Response
        # =========================

        reply = (
            response.text
            or "I could not generate a response."
        )

        return JsonResponse(
            {
                "success": True,
                "reply": reply,
            }
        )

    except PermissionDenied as error:

        print(
            "AI Permission Error:",
            repr(error),
            flush=True,
        )

        return JsonResponse(
            {
                "success": False,
                "reply": get_user_friendly_error(
                    error
                ),
            }
        )

    except ValueError as error:

        print(
            "AI Validation Error:",
            repr(error),
            flush=True,
        )

        return JsonResponse(
            {
                "success": False,
                "reply": get_user_friendly_error(
                    error
                ),
            }
        )

    except Exception as error:

        print(
            "AI Unexpected Error:",
            repr(error),
            flush=True,
        )

        return JsonResponse(
            {
                "success": False,
                "reply": get_user_friendly_error(
                    error
                ),
            }
        )