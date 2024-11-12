import xml.etree.ElementTree as ET

class XMLToMarkdownParser:
    def __init__(self, xml_file_path):
        self.tree = ET.parse(xml_file_path)
        self.root = self.tree.getroot()
        self.ns = {'y': 'http://yagsbook.sourceforge.net/xml'}  # Namespace for elements

    def parse_header(self):
        header = self.root.find('y:header', self.ns)
        if header is None:
            return ''
        
        title = header.find('y:title', self.ns).text if header.find('y:title', self.ns) is not None else ''
        tagline = header.find('y:tagline', self.ns).text if header.find('y:tagline', self.ns) is not None else ''
        summary = header.find('y:summary', self.ns).text if header.find('y:summary', self.ns) is not None else ''
        
        markdown_header = f"# {title}\n\n**{tagline}**\n\n{summary.strip()}\n\n"
        return markdown_header

    def get_text_with_nested_tags(self, element):
        """Recursively extract text from an element, including nested tags like <e>."""
        text = element.text or ""
        for child in element:
            # Wrap specific tags like <e> with asterisks or other markdown formatting as needed
            if child.tag.endswith("e"):
                text += f"*{self.get_text_with_nested_tags(child)}*"
            else:
                text += self.get_text_with_nested_tags(child)
            text += child.tail or ""
        return text

    def parse_body_sections(self, parent, level=2):
        """Parse body sections by checking for specific sect tags like sect1, sect2, sect3."""
        sections_markdown = ''
        
        for section in parent:
            tag = section.tag.split('}')[-1]  # Get tag name without namespace
            if tag.startswith("sect"):
                title = section.find('y:title', self.ns).text if section.find('y:title', self.ns) is not None else ''
                sections_markdown += f"{'#' * level} {title}\n\n"
                for para in section.findall('y:para', self.ns):
                    content = self.get_text_with_nested_tags(para)
                    sections_markdown += f"{content.strip() if content else ''}\n\n"

                # Recursive call for nested sect tags within the current section
                sections_markdown += self.parse_body_sections(section, level=level + 1)

        return sections_markdown

    def to_markdown(self):
        # Start with the header
        markdown = self.parse_header()

        # Parse the body, which contains the sect1, sect2, sect3 tags
        body = self.root.find('y:body', self.ns)
        if body is not None:
            markdown += self.parse_body_sections(body)

        return markdown

# Example usage:
# parser = XMLToMarkdownParser('path/to/character.yags')
# markdown_output = parser.to_markdown()
# print(markdown_output)