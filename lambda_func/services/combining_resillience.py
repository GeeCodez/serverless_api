# class ResilientExternalService:
#     def __init__(self, service_name, circuit_breaker, retry_config):
#         self.service_name = service_name
#         self.circuit_breaker = circuit_breaker
#         self.retry_config = retry_config
    
#     def call(self, func, fallback=None):
#         """
#         Call external service with circuit breaker and retry logic.
#         """
#         try:
#             # Use circuit breaker
#             result = self.circuit_breaker.call(
#                 lambda: retry_with_exponential_backoff(
#                     func,
#                     **self.retry_config
#                 )
#             )
#             return {"status": "success", "data": result}
#         except Exception as e:
#             # Circuit is open or all retries failed
#             if fallback:
#                 return {"status": "fallback", "data": fallback()}
#             else:
#                 return {"status": "failed", "error": str(e)}

# # Configure for different services
# payment_service = ResilientExternalService(
#     service_name="payment",
#     circuit_breaker=CircuitBreaker(failure_threshold=5, timeout=30),
#     retry_config={"max_retries": 3, "base_delay": 0.1, "max_delay": 5}
# )

# shipping_service = ResilientExternalService(
#     service_name="shipping",
#     circuit_breaker=CircuitBreaker(failure_threshold=10, timeout=60),
#     retry_config={"max_retries": 2, "base_delay": 0.2, "max_delay": 3}
# )

# # Use in Lambda handler
# def handler(event, context):
#     order_data = json.loads(event['body'])
    
#     # Critical: Payment must succeed
#     payment_result = payment_service.call(
#         lambda: process_payment(order_data['payment'])
#     )
    
#     if payment_result['status'] == 'failed':
#         return {
#             "statusCode": 500,
#             "body": json.dumps({"error": "Payment processing failed"})
#         }
    
#     # Non-critical: Shipping can use fallback
#     shipping_result = shipping_service.call(
#         lambda: calculate_shipping(order_data),
#         fallback=lambda: get_cached_shipping_rate(order_data['destination'])
#     )
    
#     return {
#         "statusCode": 200,
#         "body": json.dumps({
#             "order_id": order_data['order_id'],
#             "payment_status": payment_result['status'],
#             "shipping_rate": shipping_result['data']
#         })
#     }