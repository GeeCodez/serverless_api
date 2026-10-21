# import time
# import random

# def retry_with_exponential_backoff(func, max_retries=3, base_delay=0.1, max_delay=10):
#     """
#     Retry a function with exponential backoff and jitter.
    
#     Args:
#         func: Function to retry
#         max_retries: Maximum number of retry attempts
#         base_delay: Initial delay in seconds
#         max_delay: Maximum delay in seconds
#     """
#     for attempt in range(max_retries + 1):
#         try:
#             return func()
#         except Exception as e:
#             if attempt == max_retries:
#                 raise e
            
#             # Calculate exponential backoff with jitter
#             exponential_delay = base_delay * (2 ** attempt)
#             jitter = random.uniform(0, exponential_delay * 0.1)  # 10% jitter
#             wait_time = min(exponential_delay + jitter, max_delay)
            
#             print(f"Attempt {attempt + 1} failed. Retrying in {wait_time:.2f}s.")
#             time.sleep(wait_time)

# # Usage for shipping rate calculation
# def get_shipping_rate(order_id, destination):
#     def call_shipping_api():
#         response = shipping_api.calculate_rate(
#             order_id=order_id,
#             destination=destination
#         )
#         return response.rate
    
#     try:
#         rate = retry_with_exponential_backoff(
#             call_shipping_api,
#             max_retries=3,
#             base_delay=0.1,
#             max_delay=5
#         )
#         return {"status": "success", "rate": rate}
#     except Exception as e:
#         # All retries failed, return cached rate
#         return {"status": "fallback", "rate": get_cached_rate(destination)}