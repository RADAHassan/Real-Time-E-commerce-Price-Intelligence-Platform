{# Generic test: fail if any row has a negative value in column_name. #}
{% test is_non_negative(model, column_name) %}
    select *
    from {{ model }}
    where {{ column_name }} < 0
{% endtest %}
