1. Authentication & User Management:
POST /auth/register/wholesaler: To register a new wholesaler account.
POST /auth/register/distributor: To register a new distributor account.
POST /auth/login: To authenticate users (wholesaler, distributor, admin).
POST /auth/forgot-password: To initiate password reset.
POST /auth/reset-password: To complete password reset.
GET /users/profile: To retrieve a user's profile information.
PUT /users/profile: To update a user's profile information.

2. Product & Catalog Management:
GET /products: To retrieve a list of all products (for "All Products / Distributor Selection").
GET /distributors/{id}/products: To retrieve a list of products for a specific distributor (for "Distributor Product Catalog").
GET /products/{id}: To retrieve details of a single product (for "Wholesaler Product Detail Page").
GET /distributors: To retrieve a list of all distributors, including popular ones.
POST /distributors/{id}/products: (Distributor/Admin) To add new products to a distributor's catalog.
PUT /distributors/{id}/products/{product_id}: (Distributor/Admin) To update product details.
DELETE /distributors/{id}/products/{product_id}: (Distributor/Admin) To remove a product.

3. Order Management (Wholesaler Side):
POST /cart/add: To add a product to the wholesaler's cart.
PUT /cart/update: To update product quantities in the cart.
DELETE /cart/remove: To remove a product from the cart.
GET /cart: To retrieve the current contents of the wholesaler's cart.
POST /orders: To create a new order from the cart.
GET /orders: To retrieve a list of all orders placed by the wholesaler.
GET /orders/{id}: To retrieve details of a specific wholesaler order.
POST /orders/{id}/proof-of-payment: To upload proof of payment for an order (fallback).

4. Order Management (Distributor Side):
GET /distributor/orders/new: To retrieve new incoming orders for a distributor.
GET /distributor/orders/{id}: To retrieve details of a specific order for a distributor.
POST /distributor/orders/{id}/payment/verify: To verify payment for an order.
PUT /distributor/orders/{id}/payment/approve: To approve payment for an order.
PUT /distributor/orders/{id}/payment/reject: To reject payment for an order.
PUT /distributor/orders/{id}/status: To update the order status (e.g., "Packaging Confirmation").

5. Payment & Transaction Management:
POST /payments/bank-transfer: To log a bank transfer payment initiation (though actual transfer happens externally).
GET /transactions: To retrieve a log of all transactions (for audit purposes).

6. Notifications:
POST /notifications/send: (Internal) To send various types of notifications (e.g., new order to distributor, payment approved to wholesaler, ready for pickup to wholesaler). (This might be handled by an internal service rather than a direct API endpoint for the UI).

7. Admin Panel:
GET /admin/users: To view all users (wholesalers & distributors).
GET /admin/orders: To view all orders and their payment statuses.
POST /admin/orders/{id}/override-status: To manually override order status for dispute resolution.
PUT /admin/users/{id}/block: To block a user.
PUT /admin/users/{id}/unblock: To unblock a user.
These endpoints cover the core functionalities and data flows needed to support the user experience we've designed for SalesFunnel.