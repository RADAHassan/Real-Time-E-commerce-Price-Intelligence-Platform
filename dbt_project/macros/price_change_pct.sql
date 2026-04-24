{% macro price_change_pct(current_price, prev_price) %}
    case
        when {{ prev_price }} is null or {{ prev_price }} = 0 then null
        else round(
            ({{ current_price }} - {{ prev_price }}) / {{ prev_price }} * 100,
            2
        )
    end
{% endmacro %}
