# Domain modules

Create a module directory only when implementation begins. Do not create empty model, repository, service, or router files during bootstrap.

Member A owns `identity`, `organizations`, `master_data`, `procurement`, `approval`, `orders`, `receiving`, `inventory`, `invoices`, and `audit`.

Member B owns `suppliers`, `sourcing`, `agents`, `tools`, `rag`, `risk`, and `reporting`.

Cross-module imports may target provider `facade` modules and `app.contracts`. Imports of another module's `models`, `repository`, or private `service` are prohibited.
