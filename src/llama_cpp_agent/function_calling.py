import json
from typing import Type

from llama_cpp import LlamaGrammar
from pydantic import BaseModel

from .output_parser import parse_json_response_with_markdown_code_block_or_triple_quoted_string, parse_json_response
from .gbnf_grammar_generator.gbnf_grammar_from_pydantic_models import format_model_and_field_name, \
    generate_gbnf_grammar_and_documentation


class LlamaCppFunctionTool:
    """
    Callable class representing a tool for handling function calls in the LlamaCpp environment.

    Args:
        pydantic_model (Type[BaseModel]): The Pydantic model representing the function.
        has_markdown_code_block (bool): Flag indicating whether the response contains an extra markdown code block field.
        has_triple_quoted_string (bool): Flag indicating whether the response contains an extra triple-quoted string field.
        **additional_parameters: Additional parameters to pass to the Pydantic model during function call.

    Attributes:
        model (Type[BaseModel]): The Pydantic model representing the function parameters.
        look_for_field_string (bool): Flag indicating whether to look for a field string in the response.
        has_markdown_code_block (bool): Flag indicating whether the response contains a markdown code block.
        has_triple_quoted_string (bool): Flag indicating whether the response contains a triple-quoted string.
        additional_parameters (dict): Additional parameters to pass to the Pydantic model during function call.

    Methods:
        __call__(*args, **kwargs): Calls the Pydantic model with the provided keyword arguments.
    """
    def __init__(self, pydantic_model: Type[BaseModel], has_markdown_code_block=False, has_triple_quoted_string=False,
                 **additional_parameters):
        self.model = pydantic_model
        self.look_for_field_string = has_markdown_code_block or has_triple_quoted_string
        self.has_markdown_code_block = has_markdown_code_block
        self.has_triple_quoted_string = has_triple_quoted_string
        self.additional_parameters = additional_parameters if additional_parameters else {}

    def __call__(self, *args, **kwargs):
        """
        Calls the Pydantic model with the provided keyword arguments.

        Returns:
            BaseModel: An instance of the Pydantic model.
        """
        return self.model(**kwargs)


class LlamaCppFunctionToolRegistry:
    """
    Registry for managing LlamaCppFunctionTool instances and generating GBNF grammar.

    Methods:
        register_function_tool(function_tool: LlamaCppFunctionTool): Register a function tool.
        get_function_tool(function_name: str): Get a registered function tool by name.
        finalize(): Finalize the registry, generating the GBNF grammar and documentation.
        get_grammar() -> LlamaGrammar: Get the generated GBNF grammar.
        get_documentation() -> str: Get the documentation for the generated GBNF grammar.
        handle_function_call(function_call_response: str): Handle a function call response and return the output.

    Attributes:
        tool_root (str): Root element for the GBNF grammar.
        tool_rule_content (str): Content rule for the GBNF grammar.
        model_prefix (str): Prefix for documentation of function models.
        fields_prefix (str): Prefix for documentation of function parameter fields.
        function_tools (dict): Dictionary of registered LlamaCppFunctionTool instances.
        function_tools_containing_field_string (dict): Dictionary of registered function tools with extra markdown block or extra triple quoted strings.
        grammar (LlamaGrammar): Generated LlamaGrammar instance.
        grammar_documentation (str): Documentation for the generated GBNF grammar.
        gbnf_grammar (str): Generated GBNF grammar as a string.
    """
    def __init__(self):
        self.tool_root = "function"
        self.tool_rule_content = "function-parameters"
        self.model_prefix = "Function"
        self.fields_prefix = "Function Parameters"
        self.function_tools = {}
        self.function_tools_containing_field_string = {}
        self.grammar = None
        self.grammar_documentation = None
        self.gbnf_grammar = None

    def register_function_tool(self, function_tool: LlamaCppFunctionTool):
        """
        Register a function tool in the registry.

        Args:
            function_tool (LlamaCppFunctionTool): The function tool to register.
        """
        function_name = format_model_and_field_name(function_tool.model.__name__)
        if function_tool.look_for_field_string:
            self.function_tools_containing_field_string[function_name] = function_tool
        else:
            self.function_tools[function_name] = function_tool

    def get_function_tool(self, function_name: str):
        """
        Get a registered function tool by name.

        Args:
            function_name (str): The name of the function tool.

        Returns:
            LlamaCppFunctionTool: The registered function tool, or None if not found.
        """
        if function_name in self.function_tools:
            return self.function_tools[function_name]
        elif function_name in self.function_tools_containing_field_string:
            return self.function_tools_containing_field_string[function_name]
        else:
            return None

    def finalize(self):
        """
        Finalize the registry, generating the GBNF grammar and documentation.
        """
        pydantic_function_models = []
        look_markdown_code_block = False
        for function_tool in self.function_tools.values():
            pydantic_function_models.append(function_tool.model)
            if function_tool.look_for_field_string:
                look_markdown_code_block = True
        for function_tool in self.function_tools_containing_field_string.values():
            pydantic_function_models.append(function_tool.model)
            if function_tool.look_for_field_string:
                look_markdown_code_block = True
        gbnf_grammar, documentation = generate_gbnf_grammar_and_documentation(
            pydantic_function_models, look_markdown_code_block, look_markdown_code_block, self.tool_root,
            self.tool_rule_content, self.model_prefix,
            self.fields_prefix)

        self.grammar = LlamaGrammar.from_string(gbnf_grammar, verbose=False)
        self.grammar_documentation = documentation
        self.gbnf_grammar = gbnf_grammar

    def get_grammar(self):
        """
        Get the generated LlamaGrammar instance.

        Returns:
           LlamaGrammar: The LlamaGrammar instance.
        """
        return self.grammar

    def get_documentation(self):
        """
        Get the documentation for the provided functions for the LLM as guidance.

        Returns:
            str: The documentation for the provided functions for the LLM as guidance.
        """
        return self.grammar_documentation

    def handle_function_call(self, function_call_response: str):
        """
        Handle a function call response and return the output.

        Args:
            function_call_response (str): The function call response.

        Returns:
            str: The output of the function call or an error message.
        """
        try:
            for name, tool in self.function_tools_containing_field_string.items():

                if name in function_call_response:
                    marker = "'''" if self.function_tools_containing_field_string[name].has_triple_quoted_string else "```"
                    function_call, content = parse_json_response_with_markdown_code_block_or_triple_quoted_string(function_call_response, marker)
                    if self.function_tools_containing_field_string[function_call[self.tool_root]].has_markdown_code_block:
                        function_call[self.tool_rule_content]["markdown_code_block"] = content
                    elif self.function_tools_containing_field_string[function_call[self.tool_root]].has_triple_quoted_string:
                        function_call[self.tool_rule_content]["triple_quoted_string"] = content

                    output = self.intern_function_call(function_call, with_markdown_code_block=True)
                    return output

            function_call = parse_json_response(function_call_response)
            output = self.intern_function_call(function_call)
            return output

        except AttributeError as e:
            return f"Error: {e}"

    def intern_function_call(self, function_call: dict, with_markdown_code_block=False):
        """
        Internal method to handle a function call and return the output.

        Args:
            function_call (dict): The function call dictionary.
            with_markdown_code_block (bool): Flag indicating whether the response contains a markdown code block.

        Returns:
            str: The output of the function call or an error message.
        """
        if with_markdown_code_block:
            function_tool = self.function_tools_containing_field_string[function_call[self.tool_root]]
        else:
            function_tool = self.function_tools[function_call[self.tool_root]]
        try:
            cls = function_tool.model
            call_parameters = function_call[self.tool_rule_content]
            call = cls(**call_parameters)
            output = call.run(**function_tool.additional_parameters)
            return output
        except AttributeError as e:
            return f"Error: {e}"