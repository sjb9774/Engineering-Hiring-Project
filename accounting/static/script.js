/* Simple javascript to fade the flashed messages from the screen after a short delay */

function fade(element) {
    var op = 1;  // initial opacity
    var timer = setInterval(function () {
        if (op <= 0.05){
            clearInterval(timer);
            element.style.display = 'none';
        }
        element.style.opacity = op;
        element.style.filter = 'alpha(opacity=' + op * 100 + ")";
        op -= op * 0.1;
    }, 50);
}

function init()
{
	flashed_message = document.getElementById('error');
	setTimeout( function() {
		fade( flashed_message );
	}, 1000 );
}

window.onload = init;
