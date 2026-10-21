# def process_order(order_data):
#     """
#     Process order with graceful degradation for external services.
#     """
#     order_id = order_data['order_id']
    
#     # Step 1: Process payment (critical - must succeed)
#     try:
#         payment_result = retry_with_exponential_backoff(
#             lambda: process_payment(order_data['payment']),
#             max_retries=3
#         )
#     except Exception as e:
#         # Payment failed - cannot proceed
#         return {
#             "status": "failed",
#             "error": "Payment processing failed",
#             "order_id": order_id
#         }
    
#     # Step 2: Calculate shipping (non-critical - can use fallback)
#     try:
#         shipping_rate = retry_with_exponential_backoff(
#             lambda: get_shipping_rate(order_id, order_data['destination']),
#             max_retries=2
#         )
#     except Exception:
#         # Use cached or estimated shipping rate
#         shipping_rate = get_estimated_shipping_rate(order_data['destination'])
    
#     # Step 3: Update inventory (non-critical - can process async)
#     try:
#         update_inventory(order_data['items'])
#     except Exception:
#         # Queue for async processing
#         queue_inventory_update(order_data['items'])
    
#     # Step 4: Send confirmation email (non-critical - can process async)
#     try:
#         send_confirmation_email(order_data['customer_email'], order_id)
#     except Exception:
#         # Queue for async processing
#         queue_email(order_data['customer_email'], order_id)
    
#     return {
#         "status": "success",
#         "order_id": order_id,
#         "payment_id": payment_result['transaction_id'],
#         "shipping_rate": shipping_rate
#     }