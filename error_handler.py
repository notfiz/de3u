import time


def handle_openai(status, response, proxy, cancel_event):
    ratelimit = False
    sleep_time = 20
    if status == 401:
        if proxy:
            print("Invalid proxy password.")
            return "invalid proxy password", False
        else:
            print("Invalid API key.")
            return "invalid API key", False

    elif status == 400 or status == 429:
        if 'error' not in response:
            return "error", False
        error_message = response['error']['message']
        # different messages for different kinds of filters that gets triggered. doesn't work on reverse proxies.
        # text: Your request was rejected as a result of our safety system. Your prompt may contain text that is not allowed by our safety system.
        # image: This request has been blocked by our content filters.
        if 'code' in response and response['error']['code'] == "content_policy_violation":
            if "Your prompt may contain text" in error_message and not proxy:
                print("Filtered by text moderation. You need to modify your prompt.")
            elif "Image descriptions generated" in error_message and not proxy:
                print("Filtered by image moderation. Your request may succeed if retried.")
            else:
                print(f"Filtered. {error_message}")
            return "filtered", False

        # rate limited or quota issues
        print(f"{error_message}")
        if status == 429:
            if "rate limit" in error_message:
                ratelimit = True
            if proxy and response['error']['type'] == "proxy_rate_limited":
                ratelimit = True
                sleep_time = get_sleep_time(error_message)

            if ratelimit:
                print(f"Rate limited. Sleeping for {sleep_time} seconds.")
                for _ in range(sleep_time + 1):
                    # check for the cancel event.
                    if cancel_event.is_set():
                        break
                    time.sleep(1)
        return f"{error_message}", False

    elif response.get('error') == 'Not found':
        print("Reverse proxy not found.")
        return "reverse proxy not found", False

    else:
        print(f"Unknown error: {response}")
        return "unknown Error", False


def handle_connection(exception):
    print(f"Connection error: {exception}")
    return "connection issue", False


def get_sleep_time(message):
    try:
        start_index = message.find("Please try again in ") + len("Please try again in ")
        end_index = message.find(" seconds")
        seconds = int(message[start_index:end_index])
        return seconds
    except ValueError:
        return 20
