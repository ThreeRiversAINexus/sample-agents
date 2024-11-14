# This is a retrieval augmented generation implementation of a YAGS game master.
# YAGS is a free and open source tabletop roleplaying game system that is designed to be simple and easy to learn.

from dotenv import load_dotenv
load_dotenv()

# We are going to take the YagsRPG XML, convert it to Markdown then parse that into a vectorstore.
# from ym.parsers import XMLToMarkdownParser
# 
# xml_file_path = "datalake/yags/src/core/character.yags"
# 
# parser = XMLToMarkdownParser(xml_file_path)
# markdown_output = parser.to_markdown()
# 
# print(markdown_output)

from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI
from llama_index.core.tools import FunctionTool

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings

from llama_index.core import StorageContext, load_index_from_storage

class YagsPipeline:
    def load_documents(self, directory_path):
        documents = SimpleDirectoryReader(directory_path).load_data()
        return documents
    
    def create_index(self, documents):
        index = VectorStoreIndex.from_documents(documents)
        return index
    
    def store_indexed_data(self, index, path):
        index.storage_context.persist(persist_dir=path)
        return True

    def load_indexed_data(self, path):
        try:
            storage_context = StorageContext.from_defaults(persist_dir=path)
            index = load_index_from_storage(storage_context)
        except:
            return None
        
        return index

    def create_query_engine(self, index):
        query_engine = index.as_query_engine()
        return query_engine
    
class YagsMaster():
    def __init__(self, yags_path, yags_indexed_path):
        Settings.llm = OpenAI(model="gpt-3.5-turbo", temperature=0)
        pipeline = YagsPipeline()
        index = pipeline.load_indexed_data(yags_indexed_path)

        if index:
            print("Indexed data loaded")
        else:
            documents = pipeline.load_documents(yags_path)
            index = pipeline.create_index(documents)
            pipeline.store_indexed_data(index, yags_indexed_path)

        self.query_engine = pipeline.create_query_engine(index)
        pass

    def send_message(self, message):
        response = self.query_engine.query(message)
        return response

yagsmaster = YagsMaster("datalake/yags/release/subset", "datalake_indexed/yags")
response = yagsmaster.send_message("Explain skill difficulties and tasks and how to determine if you succeed or fail.")
print(response)

# Infinite question loop
while True:
    question = input("You: ")
    response = yagsmaster.send_message(question)
    print(response)