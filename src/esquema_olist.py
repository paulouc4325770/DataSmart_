"""Contrato de las nueve tablas originales de Olist y sus 52 campos.

Cada campo declara: tipo propuesto, descripción, unidad y disponibilidad.
La disponibilidad indica cuándo se conoce el dato, no autoriza por sí sola
su uso como predictor (los identificadores, por ejemplo, no son predictores).
"""

ARCHIVOS = {
    'clientes': 'olist_customers_dataset.csv',
    'geolocalizacion': 'olist_geolocation_dataset.csv',
    'detalles': 'olist_order_items_dataset.csv',
    'pagos': 'olist_order_payments_dataset.csv',
    'opiniones': 'olist_order_reviews_dataset.csv',
    'pedidos': 'olist_orders_dataset.csv',
    'productos': 'olist_products_dataset.csv',
    'vendedores': 'olist_sellers_dataset.csv',
    'categorias': 'product_category_name_translation.csv',
}

CLAVES = {
    'clientes': ['customer_id'],
    'detalles': ['order_id', 'order_item_id'],
    'pagos': ['order_id', 'payment_sequential'],
    'pedidos': ['order_id'],
    'productos': ['product_id'],
    'vendedores': ['seller_id'],
    'categorias': ['product_category_name'],
}

RELACIONES = [
    ('pedidos', 'customer_id', 'clientes', 'customer_id'),
    ('detalles', 'order_id', 'pedidos', 'order_id'),
    ('detalles', 'product_id', 'productos', 'product_id'),
    ('detalles', 'seller_id', 'vendedores', 'seller_id'),
    ('pagos', 'order_id', 'pedidos', 'order_id'),
    ('opiniones', 'order_id', 'pedidos', 'order_id'),
]

ESQUEMA = {
    'clientes': {
        'customer_id': ('string', 'Identificador del registro de cliente asociado al pedido.', 'identificador', 'compra'),
        'customer_unique_id': ('string', 'Identificador del comprador para agrupar sus pedidos.', 'identificador', 'compra'),
        'customer_zip_code_prefix': ('string', 'Prefijo postal del cliente, normalizado a cinco dígitos.', 'prefijo postal', 'compra'),
        'customer_city': ('string', 'Ciudad registrada del cliente.', 'texto', 'compra'),
        'customer_state': ('string', 'Estado brasileño del cliente.', 'UF', 'compra'),
    },
    'geolocalizacion': {
        'geolocation_zip_code_prefix': ('string', 'Prefijo postal repetible; no es clave en la tabla original.', 'prefijo postal', 'catalogo'),
        'geolocation_lat': ('Float64', 'Latitud observada del prefijo postal.', 'grados decimales', 'catalogo'),
        'geolocation_lng': ('Float64', 'Longitud observada del prefijo postal.', 'grados decimales', 'catalogo'),
        'geolocation_city': ('string', 'Ciudad asociada a la observación geográfica.', 'texto', 'catalogo'),
        'geolocation_state': ('string', 'Estado brasileño de la observación geográfica.', 'UF', 'catalogo'),
    },
    'detalles': {
        'order_id': ('string', 'Pedido al que pertenece el ítem.', 'identificador', 'compra'),
        'order_item_id': ('Int64', 'Posición del ítem dentro del pedido; clave junto con order_id.', 'posición', 'compra'),
        'product_id': ('string', 'Identificador del producto.', 'identificador', 'compra'),
        'seller_id': ('string', 'Identificador del vendedor del ítem.', 'identificador', 'compra'),
        'shipping_limit_date': ('datetime64[ns]', 'Fecha límite registrada para el despacho.', 'fecha y hora', 'operacion'),
        'price': ('Float64', 'Precio del artículo, sin flete.', 'BRL', 'compra'),
        'freight_value': ('Float64', 'Flete asignado al artículo.', 'BRL', 'compra'),
    },
    'pagos': {
        'order_id': ('string', 'Pedido al que corresponde el registro de pago.', 'identificador', 'compra'),
        'payment_sequential': ('Int64', 'Secuencia del pago; clave junto con order_id.', 'posición', 'pago'),
        'payment_type': ('string', 'Medio de pago registrado.', 'categoría', 'pago'),
        'payment_installments': ('Int64', 'Cantidad de cuotas registrada; se conservan los ceros y se señalan.', 'cuotas', 'pago'),
        'payment_value': ('Float64', 'Importe del registro de pago; puede haber varios por pedido.', 'BRL', 'pago'),
    },
    'opiniones': {
        'review_id': ('string', 'Identificador de reseña; puede repetirse y no se trata como clave primaria.', 'identificador', 'post_evento'),
        'order_id': ('string', 'Pedido evaluado; puede tener varias reseñas.', 'identificador', 'post_evento'),
        'review_score': ('Int64', 'Puntuación de satisfacción entre 1 y 5.', 'estrellas', 'post_evento'),
        'review_comment_title': ('string', 'Título opcional de la reseña.', 'texto', 'post_evento'),
        'review_comment_message': ('string', 'Comentario opcional; su ausencia no invalida la puntuación.', 'texto', 'post_evento'),
        'review_creation_date': ('datetime64[ns]', 'Fecha de creación de la encuesta de satisfacción.', 'fecha y hora', 'post_evento'),
        'review_answer_timestamp': ('datetime64[ns]', 'Fecha y hora de respuesta a la encuesta.', 'fecha y hora', 'post_evento'),
    },
    'pedidos': {
        'order_id': ('string', 'Clave primaria del pedido.', 'identificador', 'compra'),
        'customer_id': ('string', 'Referencia al registro transaccional del cliente.', 'identificador', 'compra'),
        'order_status': ('string', 'Estado del pedido observado en el corte del dataset.', 'categoría', 'post_evento'),
        'order_purchase_timestamp': ('datetime64[ns]', 'Fecha y hora de compra.', 'fecha y hora', 'compra'),
        'order_approved_at': ('datetime64[ns]', 'Fecha y hora de aprobación del pago.', 'fecha y hora', 'pago'),
        'order_delivered_carrier_date': ('datetime64[ns]', 'Fecha y hora de despacho al transportista.', 'fecha y hora', 'operacion'),
        'order_delivered_customer_date': ('datetime64[ns]', 'Fecha y hora real de entrega al cliente.', 'fecha y hora', 'post_evento'),
        'order_estimated_delivery_date': ('datetime64[ns]', 'Fecha de entrega prometida.', 'fecha y hora', 'compra'),
    },
    'productos': {
        'product_id': ('string', 'Clave primaria del producto.', 'identificador', 'compra'),
        'product_category_name': ('string', 'Categoría original en portugués; se conserva el faltante.', 'categoría', 'catalogo'),
        'product_name_lenght': ('Int64', 'Longitud del nombre; se conserva la ortografía original del campo.', 'caracteres', 'catalogo'),
        'product_description_lenght': ('Int64', 'Longitud de la descripción; nombre original del campo.', 'caracteres', 'catalogo'),
        'product_photos_qty': ('Int64', 'Número de fotos del producto.', 'fotos', 'catalogo'),
        'product_weight_g': ('Float64', 'Peso declarado del producto.', 'gramos', 'catalogo'),
        'product_length_cm': ('Float64', 'Longitud declarada del paquete.', 'centímetros', 'catalogo'),
        'product_height_cm': ('Float64', 'Altura declarada del paquete.', 'centímetros', 'catalogo'),
        'product_width_cm': ('Float64', 'Anchura declarada del paquete.', 'centímetros', 'catalogo'),
    },
    'vendedores': {
        'seller_id': ('string', 'Clave primaria del vendedor.', 'identificador', 'compra'),
        'seller_zip_code_prefix': ('string', 'Prefijo postal del vendedor, normalizado a cinco dígitos.', 'prefijo postal', 'compra'),
        'seller_city': ('string', 'Ciudad registrada del vendedor.', 'texto', 'compra'),
        'seller_state': ('string', 'Estado brasileño del vendedor.', 'UF', 'compra'),
    },
    'categorias': {
        'product_category_name': ('string', 'Categoría original que sirve de clave de traducción.', 'categoría', 'catalogo'),
        'product_category_name_english': ('string', 'Traducción oficial al inglés; la cobertura no es completa.', 'categoría', 'catalogo'),
    },
}
