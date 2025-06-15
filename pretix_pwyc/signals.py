@receiver(item_description, dispatch_uid="pretix_pwyc_item_description")
def add_pwyc_price_form(sender, item, variation, **kwargs):
    """Add Pay What You Can marker for JavaScript to pick up"""
    try:
        if not is_pwyc_item(sender, item):
            return ""

        # Get PWYC settings for this item
        min_amount = sender.settings.get(f'pwyc_min_amount_{item.pk}', '')
        suggested_amount = sender.settings.get(f'pwyc_suggested_amount_{item.pk}', '')
        explanation = sender.settings.get(f'pwyc_explanation_{item.pk}', '')

        logger.info(f"PWYC: Adding JavaScript PWYC form for item {item.pk}")

        # Return a simple data container that JavaScript can read
        from django.utils.safestring import mark_safe
        from django.utils.html import escape
        import json

        data = {
            'item_id': item.pk,
            'min_amount': min_amount,
            'suggested_amount': suggested_amount,
            'explanation': explanation,
            'currency': sender.currency,
        }

        # Create safe JSON string
        json_data = escape(json.dumps(data))

        html = f'''
        <div class="pwyc-container-{item.pk}">
            <div class="pwyc-data" style="display: none;" data-pwyc='{json_data}'></div>
            <div id="pwyc-form-{item.pk}"></div>
        </div>
        <script>
        (function() {{
            // Wait for DOM to be ready
            function initPWYC() {{
                var container = document.querySelector('.pwyc-container-{item.pk}');
                if (!container) return;

                var dataEl = container.querySelector('.pwyc-data[data-pwyc]');
                var formContainer = container.querySelector('#pwyc-form-{item.pk}');

                if (dataEl && formContainer && !formContainer.innerHTML) {{
                    try {{
                        var data = JSON.parse(dataEl.getAttribute('data-pwyc'));
                        var formHtml = [
                            '<div class="alert alert-info" style="margin-top: 15px;">',
                            '<h4><i class="fa fa-heart"></i> Pay What You Can</h4>'
                        ];

                        if (data.explanation) {{
                            formHtml.push('<p>' + data.explanation + '</p>');
                        }}

                        formHtml = formHtml.concat([
                            '<div class="form-group">',
                            '<label>Choose your price:</label>',
                            '<div class="input-group">',
                            '<input type="number" class="form-control pwyc-price-input" step="0.01"',
                            ' min="' + (data.min_amount || '0') + '"',
                            ' value="' + (data.suggested_amount || '') + '"',
                            ' data-item-id="' + data.item_id + '"',
                            ' placeholder="Enter amount">',
                            '<span class="input-group-addon">' + data.currency + '</span>',
                            '</div>'
                        ]);

                        if (data.min_amount) {{
                            formHtml.push('<small class="help-block">Minimum: ' + data.min_amount + ' ' + data.currency + '</small>');
                        }}

                        if (data.suggested_amount) {{
                            formHtml.push('<small class="help-block">Suggested: ' + data.suggested_amount + ' ' + data.currency + '</small>');
                        }}

                        formHtml.push('</div></div>');

                        formContainer.innerHTML = formHtml.join('');

                        // Add event listener for price changes
                        var priceInput = formContainer.querySelector('.pwyc-price-input');
                        if (priceInput) {{
                            priceInput.addEventListener('change', function() {{
                                var price = parseFloat(this.value);
                                var itemId = this.getAttribute('data-item-id');
                                var minPrice = parseFloat(this.getAttribute('min')) || 0;

                                if (isNaN(price) || price < 0) {{
                                    alert('Please enter a valid price.');
                                    this.value = data.suggested_amount || minPrice;
                                    return;
                                }}

                                if (price < minPrice) {{
                                    alert('Price must be at least ' + minPrice + ' ' + data.currency);
                                    this.value = minPrice;
                                    price = minPrice;
                                }}

                                // Store the custom price in session via AJAX
                                fetch('/pwyc/set-price/', {{
                                    method: 'POST',
                                    headers: {{
                                        'Content-Type': 'application/json',
                                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                                    }},
                                    body: JSON.stringify({{
                                        'item_id': itemId,
                                        'price': price
                                    }})
                                }}).then(function(response) {{
                                    if (response.ok) {{
                                        console.log('PWYC price set:', price);
                                        // Show success feedback
                                        var feedback = formContainer.querySelector('.pwyc-feedback');
                                        if (!feedback) {{
                                            feedback = document.createElement('div');
                                            feedback.className = 'pwyc-feedback alert alert-success';
                                            feedback.style.marginTop = '10px';
                                            formContainer.appendChild(feedback);
                                        }}
                                        feedback.textContent = 'Custom price saved: ' + price + ' ' + data.currency;
                                        setTimeout(function() {{
                                            if (feedback.parentNode) {{
                                                feedback.parentNode.removeChild(feedback);
                                            }}
                                        }}, 3000);
                                    }} else {{
                                        console.error('Failed to set PWYC price');
                                        alert('Failed to save price. Please try again.');
                                    }}
                                }}).catch(function(error) {{
                                    console.error('Error setting PWYC price:', error);
                                    alert('Failed to save price. Please try again.');
                                }});
                            }});
                        }}
                    }} catch (e) {{
                        console.error('PWYC: Error parsing data or creating form:', e);
                    }}
                }}
            }}

            // Try to initialize immediately
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', initPWYC);
            }} else {{
                initPWYC();
            }}
        }})();
        </script>
        '''

        return mark_safe(html)

    except Exception as e:
        logger.error(f"PWYC: Error adding price form for item {item.pk}: {e}")
        import traceback
        logger.error(f"PWYC: Traceback: {traceback.format_exc()}")
        return ""
