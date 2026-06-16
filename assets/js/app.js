$(function () {
    const $navigation = $("#mainNavigation");

    $navigation.find('a[href^="#"]').on("click", function () {
        const navigation = bootstrap.Collapse.getInstance($navigation[0]);

        if (navigation) {
            navigation.hide();
        }
    });
});
