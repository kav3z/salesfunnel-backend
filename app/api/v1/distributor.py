# Distributor endpoints
# GET /api/v1/distributor/dashboard - Get dashboard stats
# GET /api/v1/distributor/orders - List received orders (with filters)
# GET /api/v1/distributor/orders/{id} - Get order details
# PATCH /api/v1/distributor/orders/{id}/status - Update order status
# GET /api/v1/distributor/payments - List payments pending verification
# GET /api/v1/distributor/payments/{id} - Get payment details
# PATCH /api/v1/distributor/payments/{id}/verify - Verify payment
# PATCH /api/v1/distributor/payments/{id}/approve - Approve payment
# PATCH /api/v1/distributor/payments/{id}/reject - Reject payment
# POST /api/v1/distributor/orders/{id}/package - Mark order as packaged/ready
# GET /api/v1/distributor/products - List my products
# POST /api/v1/distributor/products - Add new product
# PUT /api/v1/distributor/products/{id} - Update product
# DELETE /api/v1/distributor/products/{id} - Delete product
# GET /api/v1/distributor/profile - Get my profile
# PUT /api/v1/distributor/profile - Update my profile (bank details, etc.)
# GET /api/v1/distributor/notifications - Get my notifications
# PATCH /api/v1/distributor/notifications/{id}/read - Mark notification as read
