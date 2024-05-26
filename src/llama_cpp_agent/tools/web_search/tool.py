from llama_cpp_agent import LlamaCppAgent, MessagesFormatterType
from llama_cpp_agent.providers.provider_base import LlmProvider, LlmProviderId
from .web_search_interfaces import WebCrawler, WebSearchProvider
from .default_web_crawlers import TrafilaturaWebCrawler
from .default_web_search_providers import DDGWebSearchProvider
from ...prompt_templates import summarizing_system_prompt


class WebSearchTool:

    def __init__(self, llm_provider: LlmProvider, message_formatter_type: MessagesFormatterType,
                 web_crawler: WebCrawler = None, web_search_provider: WebSearchProvider = None, temperature: int = 0.45,
                 top_p: int = 0.95,
                 top_k: int = 40, max_tokens_search_results: int = 7500,
                 max_tokens_per_summary: int = 750):
        self.llm_provider = llm_provider
        self.summarising_agent = LlamaCppAgent(llm_provider, debug_output=True,
                                               system_prompt=summarizing_system_prompt,
                                               predefined_messages_formatter_type=message_formatter_type)
        if web_crawler is None:
            self.web_crawler = TrafilaturaWebCrawler()
        else:
            self.web_crawler = web_crawler

        if web_search_provider is None:
            self.web_search_provider = DDGWebSearchProvider()
        else:
            self.web_search_provider = web_search_provider

        self.max_tokens_search_results = max_tokens_search_results
        settings = llm_provider.get_provider_default_settings()
        provider_id = llm_provider.get_provider_identifier()
        settings.temperature = temperature
        settings.top_p = top_p
        settings.top_k = top_k

        if provider_id == LlmProviderId.llama_cpp_server:
            settings.n_predict = max_tokens_per_summary
        elif provider_id == LlmProviderId.tgi_server:
            settings.max_new_tokens = max_tokens_per_summary
        else:
            settings.max_tokens = max_tokens_per_summary

        self.settings = settings

    def search_web(self, search_query: str):
        """
        Search the web for information.
        Args:
            search_query (str): Search query to search for.
        """
        results = self.web_search_provider.search_web(search_query)
        result_string = ''
        for res in results:
            web_info = self.web_crawler.get_website_content_from_url(res)
            if web_info != "":
                web_info = self.summarising_agent.get_chat_response(
                    f"Please summarize the following Website content and extract relevant information to this query:'{search_query}'.\n\n" + web_info,
                    add_response_to_chat_history=False, add_message_to_chat_history=False, llm_sampling_settings=self.settings)
                result_string += f"\n\n{web_info.strip()}"

        res = result_string.strip()
        tokens = self.llm_provider.tokenize(res)
        original_prompt_token_count = len(tokens)
        remove_char_count = 0
        has_remove_char = False
        if original_prompt_token_count > self.max_tokens_search_results:
            has_remove_char = True
            while True:
                if self.max_tokens_search_results >= len(tokens):
                    break
                else:
                    remove_char_count += 50
                    tokens = self.llm_provider.tokenize(res[:remove_char_count])
        if not has_remove_char:
            return "\nResults of searching the web:\n\n" + res
        return "\nResults of searching the web:\n\n" + res[:remove_char_count]

    def get_tool(self):
        return self.search_web


