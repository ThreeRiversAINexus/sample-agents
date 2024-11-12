
# This is a retrieval augmented generation implementation
# We are going to take the YagsRPG XML, convert it to Markdown then parse that into a vectorstore.

from ym.parsers import XMLToMarkdownParser

xml_file_path = "datalake/yags/src/core/character.yags"

parser = XMLToMarkdownParser(xml_file_path)
markdown_output = parser.to_markdown()

print(markdown_output)