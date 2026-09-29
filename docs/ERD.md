# Smart Delivery & Logistics Management System - ERD

## Main Entities

### User
- id (PK)
- username
- email
- role
- password

### CustomerProfile
- id (PK)
- user_id (FK -> User)
- company_name
- notes

### DriverProfile
- id (PK)
- user_id (FK -> User)
- vehicle_type
- vehicle_plate
- is_available
- is_active
- notes

### Address
- id (PK)
- label
- street
- city
- state
- postal_code
- country
- created_by (FK -> User)

### Delivery
- id (PK)
- customer_id (FK -> User)
- pickup_address_id (FK -> Address)
- destination_address_id (FK -> Address)
- package_description
- weight_kg
- status
- is_delayed
- notes
- expected_delivery_at
- delivered_at
- created_at
- updated_at

### DeliveryAssignment
- id (PK)
- delivery_id (FK -> Delivery)
- driver_id (FK -> DriverProfile)
- assigned_at
- unassigned_at
- is_active

### DeliveryStatusHistory
- id (PK)
- delivery_id (FK -> Delivery)
- status
- note
- created_at

### Notification
- id (PK)
- user_id (FK -> User)
- title
- message
- is_read
- created_at

## Relationships

- User 1 ---- 1 CustomerProfile
- User 1 ---- 1 DriverProfile
- User 1 ---- N Address
- User 1 ---- N Delivery
- Delivery N ---- 1 Address (Pickup)
- Delivery N ---- 1 Address (Destination)
- Delivery 1 ---- N DeliveryAssignment
- DriverProfile 1 ---- N DeliveryAssignment
- Delivery 1 ---- N DeliveryStatusHistory
- User 1 ---- N Notification