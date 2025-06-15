$(document).ready(function() {
    // Handle suggested price click to auto-fill the price field
    $('.pwyc-suggested-price').click(function(e) {
        e.preventDefault();
        var suggestedPrice = $(this).data('price');
        var itemId = $(this).data('item');
        $('#id_pwyc_' + itemId + '-pwyc_price').val(suggestedPrice);
    });

    // Add visual feedback when price is entered
    $('input[id$="-pwyc_price"]').on('input', function() {
        var value = parseFloat($(this).val());
        var minValue = parseFloat($(this).data('min-value') || 0);

        if (isNaN(value)) {
            $(this).closest('.form-group').removeClass('has-success has-error');
        } else if (value < minValue) {
            $(this).closest('.form-group').removeClass('has-success').addClass('has-error');
        } else {
            $(this).closest('.form-group').removeClass('has-error').addClass('has-success');
        }
    });

    // In admin panel, highlight rows of items with PWYC enabled
    if ($('body').hasClass('pretixcontrol')) {
        $('tr[data-pwyc-enabled="true"]').addClass('pwyc-enabled');
    }
});
