# Example that uses the StructuredOutputAgent class to create a dataset entry of a book, out of unstructured data.

from enum import Enum

from llama_cpp import Llama
from pydantic import BaseModel, Field

from llama_cpp_agent.providers.llama_cpp_server_provider import LlamaCppServerLLMSettings
from llama_cpp_agent.structured_output_agent import StructuredOutputAgent


# Example enum for our output model
class Category(Enum):
    Fiction = "Fiction"
    NonFiction = "Non-Fiction"


# Example output model
class Book(BaseModel):
    """
    Represents an entry about a book.
    """
    title: str = Field(..., description="Title of the book.")
    author: str = Field(..., description="Author of the book.")
    published_year: int = Field(..., description="Publishing year of the book.")
    keywords: list[str] = Field(..., description="A list of keywords.")
    category: Category = Field(..., description="Category of the book.")
    summary: str = Field(..., description="Summary of the book.")


main_model = LlamaCppServerLLMSettings(
    completions_endpoint_url="http://127.0.0.1:8080/completion"
)

structured_output_agent = StructuredOutputAgent(main_model, debug_output=True)

text = """The Feynman Lectures on Physics is a physics textbook based on some lectures by Richard Feynman, a Nobel laureate who has sometimes been called "The Great Explainer". The lectures were presented before undergraduate students at the California Institute of Technology (Caltech), during 1961–1963. The book's co-authors are Feynman, Robert B. Leighton, and Matthew Sands."""
print(structured_output_agent.create_object(Book, text))
