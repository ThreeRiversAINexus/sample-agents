import os
import logging
from typing import Optional
from nicegui import run
from .runpod_api import RunPodAPI

class ImageGenerator:
    def __init__(self, endpoint_id=None):
        self.api = RunPodAPI(endpoint_id=endpoint_id)
        self.logger = logging.getLogger('discussion_show.image_generator')

    def truncate_prompt(self, prompt: str, max_words: int = 30) -> str:
        """Truncate prompt to avoid CLIP token limit issues."""
        words = prompt.split()
        if len(words) > max_words:
            self.logger.info(f"Truncating prompt from {len(words)} to {max_words} words")
            return ' '.join(words[:max_words])
        return prompt

    async def generate_image(self, context: str) -> Optional[str]:
        """Generate an image from the given context."""
        def _generate():
            try:
                # Truncate prompt to avoid token limit issues
                # truncated_prompt = self.truncate_prompt(context)
                truncated_prompt = context
                self.logger.debug(f"Using truncated prompt: {truncated_prompt}")

                # Run SDXL with the truncated prompt
                result = self.api.run_sdxl(truncated_prompt)
                
                if not result:
                    self.logger.error("Failed to generate image")
                    return None

                # Extract image data from result
                if isinstance(result, list) and result:
                    image_data = result[0].get("image", None)
                elif isinstance(result, dict):
                    image_data = result.get("image") or result.get("image_url")
                else:
                    image_data = result

                if image_data:
                    self.logger.info("Successfully generated image")
                    return image_data
                else:
                    self.logger.error(f"No image in output: {result}")
                    return None

            except Exception as e:
                self.logger.error(f"Error in generate_image: {str(e)}")
                return None

        return await run.io_bound(_generate)
