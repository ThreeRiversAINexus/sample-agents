import requests

class RunPodAPI:
    def __init__(self, api_key, base_url="https://api.runpod.ai/v2"):
        self.api_key = api_key
        self.base_url = base_url

    def start_job(self, endpoint_id, prompt):
        url = f"{self.base_url}/{endpoint_id}/runsync"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        data = {
            "input": {
                "prompt": prompt
            }
        }
        response = requests.post(url, headers=headers, json=data)
        return response.json()

    def check_status(self, endpoint_id, job_status_id):
        url = f"{self.base_url}/{endpoint_id}/status/{job_status_id}"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        response = requests.get(url, headers=headers)
        return response.json()

    def decode_image(self, json_data, remove_prefix=True):
        try:
            base64_image = json_data["output"]["image_url"]
            if remove_prefix:
                base64_image = base64_image.replace("data:image/png;base64,", "")
            return base64_image
        except KeyError as e:
            print(f"Error in JSON structure: {e}")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def get_results(self, endpoint_id, job_status_id, remove_prefix=True):
        json_data = self.check_status(endpoint_id, job_status_id)
        while json_data.get("status") != "COMPLETED":
            print("Waiting...")
            json_data = self.check_status(endpoint_id, job_status_id)
        return self.decode_image(json_data, remove_prefix)