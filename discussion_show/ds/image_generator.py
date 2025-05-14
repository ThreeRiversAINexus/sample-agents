import os
import logging
import base64
from typing import Optional
from nicegui import run
from openai import OpenAI
from .runpod_api import RunPodAPI

class ImageGenerator:
    def __init__(self, endpoint_id=None):
        self.image_provider = os.getenv("IMAGE_PROVIDER", "runpod")
        self.logger = logging.getLogger('discussion_show.image_generator')
        self.logger.info(f"Using image provider: {self.image_provider}")

        if self.image_provider == "runpod":
            self.api = RunPodAPI(endpoint_id=endpoint_id)
        elif self.image_provider == "openai":
            # OpenAI client will automatically pick up OPENAI_API_KEY from env
            self.openai_client = OpenAI() 
        else:
            raise ValueError(f"Unsupported image provider: {self.image_provider}")

    def _generate_openai_image(self, prompt: str) -> Optional[str]:
        """Generates an image using the OpenAI API."""
        try:
            self.logger.debug(f"Generating OpenAI image with prompt: {prompt}")
            # Note: Consider adding error handling for API key issues if client init fails
            if not hasattr(self, 'openai_client'):
                 self.logger.error("OpenAI client not initialized. Check IMAGE_PROVIDER and OPENAI_API_KEY.")
                 return None

            result = self.openai_client.images.generate(
                model="dall-e-3",  # Or use a configurable model
                prompt=prompt,
                n=1,
                response_format="b64_json" # Request base64 directly
            )
            
            if result.data and result.data[0].b64_json:
                image_base64 = result.data[0].b64_json
                self.logger.info("Successfully generated OpenAI image")
                # Return the base64 string directly
                return image_base64 
            else:
                self.logger.error(f"No image data in OpenAI response: {result}")
                return None
        except Exception as e:
            self.logger.error(f"Error in _generate_openai_image: {str(e)}", exc_info=True)
            return None

    def truncate_prompt(self, prompt: str, max_words: int = 30) -> str:
        """Truncate prompt to avoid CLIP token limit issues."""
        words = prompt.split()
        if len(words) > max_words:
            self.logger.info(f"Truncating prompt from {len(words)} to {max_words} words")
            return ' '.join(words[:max_words])
        return prompt

    async def generate_image(self, context: str) -> Optional[str]:
        """Generate an image from the given context using the configured provider."""
        def _generate():
            image_data = None
            try:
                # Truncate prompt if needed (currently commented out)
                # truncated_prompt = self.truncate_prompt(context)
                truncated_prompt = context
                self.logger.debug(f"Using prompt: {truncated_prompt}")

                if self.image_provider == "openai":
                    # Use the new OpenAI method (synchronous)
                    image_data = self._generate_openai_image(truncated_prompt)
                
                elif self.image_provider == "runpod":
                    # Use the existing RunPod method
                    # Ensure RunPodAPI client is initialized
                    if not hasattr(self, 'api'):
                        self.logger.error("RunPod API client not initialized. Check IMAGE_PROVIDER and RunPod config.")
                        return None
                    
                    result = self.api.run_sdxl(truncated_prompt)
                    
                    if not result:
                        self.logger.error("Failed to generate RunPod image")
                        return None

                    # Extract image data from RunPod result
                    if isinstance(result, list) and result:
                        image_data = result[0].get("image", None)
                    elif isinstance(result, dict):
                        image_data = result.get("image") or result.get("image_url")
                    else: # Assuming result might be the base64 string directly
                        image_data = result 

                else:
                    # This case should ideally be caught in __init__, but added for safety
                    self.logger.error(f"Invalid image provider configured: {self.image_provider}")
                    return None

                # Check and log final result
                if image_data:
                    self.logger.info(f"Successfully generated image using {self.image_provider}")
                    return image_data
                else:
                    self.logger.error(f"Failed to get image data using {self.image_provider}")
                    return None

            except Exception as e:
                self.logger.error(f"Error during image generation with {self.image_provider}: {str(e)}", exc_info=True)
                return None

        # Run the appropriate generation logic in a separate thread
        return await run.io_bound(_generate)
