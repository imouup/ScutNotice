import requests

def test_youth_notice():
    # Replace the base_url with the actual address of your dataGet service
    # Common local addresses: http://127.0.0.1:8000 or http://localhost:5000
    base_url = "http://127.0.0.1:5000" 
    url = f"{base_url}/scut/youth_notice"

    try:
        print(f"Sending GET request to: {url}")
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            print("Success!")
            # Assuming the response is JSON
            try:
                data = response.json()
                print("Response Data:")
                print(data)
            except ValueError:
                print("Response content (not JSON):")
                print(response.text)
        else:
            print(f"Failed with status code: {response.status_code}")
            print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_youth_notice()