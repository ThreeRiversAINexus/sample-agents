import os
import time
import logging
import requests
from typing import Optional, Dict, Any

class RunPodAPI:
    def __init__(self, endpoint_id: Optional[str] = None, api_key: Optional[str] = None):
        self.endpoint_id = endpoint_id or os.environ.get("RUNPOD_ENDPOINT")
        self.api_key = api_key or os.environ.get("RUNPOD_API_KEY")
        self.logger = logging.getLogger('discussion_show.runpod_api')
        
        if not self.endpoint_id or not self.api_key:
            raise ValueError("Both endpoint_id and api_key are required")

    def _get_headers(self) -> Dict[str, str]:
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

    def _handle_response(self, response: requests.Response, operation: str) -> Optional[Dict]:
        """Handle API response with proper logging."""
        try:
            response.raise_for_status()
            result = response.json()
            self.logger.debug(f"RunPod {operation} response: {result}")
            return result
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error in {operation}: {e.response.status_code} - {e.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error in {operation}: {str(e)}")
            return None
        except ValueError as e:
            self.logger.error(f"JSON decode error in {operation}: {str(e)}")
            return None

    def run_inference(self, input_data: Dict[str, Any]) -> Optional[Dict]:
        """Start a new inference job."""
        url = f"https://api.runpod.ai/v2/{self.endpoint_id}/run"
        self.logger.info(f"Starting inference with input: {input_data}")
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json={"input": input_data},
                timeout=30
            )
            return self._handle_response(response, "inference start")
        except Exception as e:
            self.logger.error(f"Failed to start inference: {str(e)}")
            return None

    def get_status(self, job_id: str) -> Optional[Dict]:
        """Check the status of a job."""
        url = f"https://api.runpod.ai/v2/{self.endpoint_id}/status/{job_id}"
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            result = self._handle_response(response, "status check")
            if result:
                self.logger.debug(f"Job {job_id} status: {result.get('status')}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to check status: {str(e)}")
            return None

    def get_result(self, job_id: str, max_retries: int = 30, retry_delay: int = 2) -> Optional[Dict]:
        """Get the result of a job with retries."""
        retries = 0
        while retries < max_retries:
            status = self.get_status(job_id)
            if not status:
                return None

            job_status = status.get("status")
            if job_status == "COMPLETED":
                output = status.get("output")
                self.logger.info(f"Job {job_id} completed successfully")
                self.logger.debug(f"Job output: {output}")
                return output
            elif job_status in ["FAILED", "CANCELLED"]:
                error = status.get("error", "Unknown error")
                self.logger.error(f"Job {job_id} failed: {error}")
                return None

            retries += 1
            self.logger.debug(f"Job {job_id} still running, attempt {retries}/{max_retries}")
            time.sleep(retry_delay)

        self.logger.error(f"Job {job_id} timed out after {max_retries} attempts")
        return None

    def run_sdxl(self, prompt: str, **kwargs) -> Optional[Dict]:
        """Run Stable Diffusion XL with default parameters."""
        default_params = {
            "prompt": prompt,
            "negative_prompt": "blurry, bad quality, distorted",
            "num_inference_steps": 20,
            # "guidance_scale": 7.5,
            "width": 512,
            "height": 512,
            # "seed": int(time.time()),
            "num_images": 1
            # "scheduler": "DPMSolverMultistep",
            # "safety_checker": False,
            # "enhance_prompt": False,
            # "multi_lingual": False,
            # "panorama": False,
            # "self_attention": False,
            # "upscale": False,
            # "embeddings_model": None,
            # "lora_model": None,
            # "tomesd": True,
            # "clip_skip": 2
            # "use_karras_sigmas": False,
            # "vae": None,
            # "use_fp16": True
        }
        
        # Update defaults with any provided kwargs
        input_data = {**default_params, **kwargs}
        self.logger.info(f"Running SDXL with prompt: {prompt}")
        self.logger.debug(f"Full parameters: {input_data}")
        
        # Start the job
        job = self.run_inference(input_data)
        if not job:
            return None
            
        job_id = job.get("id")
        if not job_id:
            self.logger.error("No job ID in response")
            return None
            
        # Get the result
        return self.get_result(job_id)
