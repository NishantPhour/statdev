var django_ajax_form = {
      var: {
          form_html: '',
          url: '',
	  title: '',
	  loading_html: '<div class="modal-body" style="overflow: auto;" id="modal-body"><center><h4>Please Wait</h4><br><img src="/static/images/rainbow-spinner.gif"><br><br></center></div>'
      },
      OpenForm: function(url,title) {
	console.log("OpenForm");
        console.log(url);
        $('#PLvesselModal').remove();
        $('#vesselModal').remove();

        var htmlvalue = "";
            htmlvalue += '<div id="PLvesselModal" class="modal fade" role="dialog">';
            htmlvalue += '   <div class="modal-dialog modal-lg" id="modal-dialog">';
            htmlvalue += '       <div class="modal-content" id="modal-content">';
            htmlvalue += django_ajax_form.var.loading_html;
            htmlvalue += '       </div>';
            htmlvalue += '   </div>';
            htmlvalue += '</div>';
   
          if ($('#PLvesselModal').length != 0) {
            $('html').prepend(htmlvalue);
          }

        $('#PLvesselModal').modal({
             show: true,
             backdrop: 'static',
             keyboard: false

        });
       
       $('#modal-dialog').width('300px');




        $('.modal-body').height('auto');
        $('#PLvesselModal').modal("show").addClass("in");
	django_ajax_form.var.url = url;
	django_ajax_form.var.title = title;

        //  var crispy_form_load = $.get( "/applications/272/vessel/" ).responseText;
        //  alert(crispy_form_load);
        // $('#vesselModal').remove();
        if (title == null) {
	    title="";
	}
	$.ajax({
	    url: url,
	    //async: false,
	    success: function(data) {
        	  django_ajax_form.var.form_html = data;
		  //  $('#vesselModal').remove();
      
// $('#PLvesselModal').hide();
		  $('#PLvesselModal').remove();
		  $('.modal-backdrop').remove();
                  django_ajax_form.CloseForm();
		  $('#vesselModal').remove();
        // var loader_html = '<div id="popup_loader" style="display: none;">LOADING</div>';
        var csrfmiddlewaretoken = $("input[name=csrfmiddlewaretoken]").val();

        var htmlvalue = "";
            htmlvalue += '<div id="vesselModal" class="modal fade" role="dialog">';
            htmlvalue += '<div class="modal-dialog modal-lg" id="modal-dialog">';
            htmlvalue += '    <div class="modal-content" id="modal-content">';
            htmlvalue += '      <div class="modal-header">';
            htmlvalue += '        <h4 class="modal-title" id="modal-popup-title">'+title+'</h4>';
            htmlvalue += '        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>';
            htmlvalue += '      </div>';
            htmlvalue += '      <div class="modal-body" style="overflow: auto;" id="modal-body">';
            htmlvalue += django_ajax_form.var.form_html;
            htmlvalue += '<form action="/applications-uploads/" method="post" enctype="multipart/form-data" id="upload_form">';
            htmlvalue += '<input type="hidden" name="csrfmiddlewaretoken" value="'+csrfmiddlewaretoken+'" />';
            htmlvalue += '</form>';
            htmlvalue += '<BR><BR>';
            htmlvalue += '<BR><BR>';
            htmlvalue += '</div>';
            htmlvalue += '<div class="modal-footer">';
            htmlvalue += '<BR><BR><button name="close" type="button" class="btn btn-primary" value="Close" class="close" data-bs-dismiss="modal"  value="Close">Close</button>';
            htmlvalue += '</div>';
            htmlvalue += '</div>';
            htmlvalue += '</div>';
            htmlvalue += '</div>';
            htmlvalue += '</div>';

            $('html').prepend(htmlvalue);
	    $('#vesselModal').modal({
                 show: 'false',
                 backdrop: 'static',
		 keyboard: false

            });
            $( window ).resize(function() {
                             var modalbodyheight = window.innerHeight * 0.7;
                             $('.modal-body').height(modalbodyheight+'px');
            });
            var modalbodyheight = window.innerHeight * 0.7;
            $('.modal-body').height(modalbodyheight+'px');



 // $('#vesselModal').modal('show');
 $('#vesselModal').modal("show").addClass("in");

$('#id_form_modals').submit(function(event) {
event.preventDefault();
});


$('.ajax-submit').on("click", function(event) {
    django_ajax_form.saveForm();
});

$('.ajax-close').on("click", function(event) {
    django_ajax_form.CloseForm();
});
$("#vesselModal").on("hidden.bs.modal", function () {
    // $('.modal-body').html('');
    $('.modal-body').height('auto');
    // put your default event here
});

    $(function() {
        // Initialise datepicker widgets.
        $(".dateinput").datepicker({
            format: 'dd/mm/yyyy',
            autoclose: true,
            todayHighlight: true
        });
    });
	// end of ajax success

            }
 });

      },
      saveForm: function()  { 

console.log("WAITING");
// django_ajax_form.CloseForm()
var form_data = new FormData($('#id_form_modals')[0]);
//$('#vesselModal').modal('hide');
$('#modal-content').html(django_ajax_form.var.loading_html);
$('#modal-dialog').width('300px');	      
//	     $('#modal-content').width('300px') 	     

// django_ajax_form.CloseForm()	   
$('#popup_loader').modal("show").addClass("in");
$.ajax({
url : django_ajax_form.var.url,
type: "POST",
data : form_data,
contentType: false,
cache: false,
// async: false,
processData:false,
xhr: function() {
//upload Progress
var xhr = $.ajaxSettings.xhr();
return xhr;
},
mimeType:"multipart/form-data"
}).done(function(res) { //
        // django_form_checks.var.form_changed = 'changed';
//        console.log('upload complete');
//        var input_array =[];
console.log('DONE');        
django_ajax_form.CloseForm();
// $('#vesselModal').show();
//$('#vesselModal').modal('hide');
// $('#popup_loader').hide();

if (res.indexOf('alert-danger') >= 0 || res.indexOf('id="error') >= 0) { 
        console.log("ERROR Found in response");
        var csrfmiddlewaretoken = $("input[name=csrfmiddlewaretoken]").val();

	$('#vesselModal').remove();
        $('.modal-backdrop').remove();
        console.log(res);
        var htmlvalue = "";
            htmlvalue += '<div id="vesselModal" class="modal fade" role="dialog">';
            htmlvalue += '<div class="modal-dialog modal-lg" id="modal-dialog">';
            htmlvalue += '    <div class="modal-content" id="modal-content">';
            htmlvalue += '      <div class="modal-header">';
            htmlvalue += '        <h4 class="modal-title" id="modal-popup-title">'+django_ajax_form.var.title+'</h4>';
            htmlvalue += '        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>';
            htmlvalue += '      </div>';
            htmlvalue += '      <div class="modal-body" style="overflow: auto;" id="modal-body">';
            htmlvalue += res;
            htmlvalue += '<form action="/applications-uploads/" method="post" enctype="multipart/form-data" id="upload_form">';
            htmlvalue += '<input type="hidden" name="csrfmiddlewaretoken" value="'+csrfmiddlewaretoken+'" />';
            htmlvalue += '</form>';
            htmlvalue += '<BR><BR>';
            htmlvalue += '<BR><BR>';
            htmlvalue += '</div>';
            htmlvalue += '<div class="modal-footer">';
            htmlvalue += '<BR><BR><button name="close" type="button" class="btn btn-primary" value="Close" class="close" data-bs-dismiss="modal"  value="Close">Close</button>';
            htmlvalue += '</div>';
            htmlvalue += '</div>';
            htmlvalue += '</div>';
            htmlvalue += '</div>';
            htmlvalue += '</div>';
            $('html').prepend(htmlvalue);

            $('#vesselModal').modal({
		      show: 'false',                  
		      backdrop: 'static',
	              keyboard: false
	    });

            $( window ).resize(function() {
	             var modalbodyheight = window.innerHeight * 0.7;
	           $('.modal-body').height(modalbodyheight+'px');
	    });
	    var modalbodyheight = window.innerHeight * 0.7;
	    $('.modal-body').height(modalbodyheight+'px');


if (typeof loadForm == 'function') { 
  loadForm(); 
} else {
  console.log("no loadForm");
}
$('#id_form_modals').submit(function(event) {
 event.preventDefault();
});


$('.ajax-submit').on("click", function(event) {
django_ajax_form.saveForm();

});
$('.ajax-close').on("click", function(event) {
 django_ajax_form.CloseForm();

});
$("#vesselModal").on("hidden.bs.modal", function () {
	    // $('.modal-body').html('');
	    $('.modal-body').height('auto');
	    // put your default event here
});
	

    $(function() {
        // Initialise datepicker widgets.
        $(".dateinput").datepicker({
            format: 'dd/mm/yyyy',
            autoclose: true,
            todayHighlight: true
        });
    });


        // $(form_id)[0].reset(); //reset form
        // $(result_output).html(res); //output response from server
//        var obj = JSON.parse(res);
 //       var input_id_obj = $('#'+input_id+'_json').val();

//        if (upload_type == 'multiple') {

 //       if (input_id_obj.length > 0) {
 //       	input_array = JSON.parse(input_id_obj);
 //       }

//        input_array.push(obj);
 //       console.log(obj['doc_id']);
 //       console.log(input_id);

   //     } else {
        //        input_array = obj
  //      }

    //    $('#'+input_id+'_json').val(JSON.stringify(input_array));
    //    submit_btn.val("Upload").prop( "disabled", false); //enable submit button once ajax is done
    //    ajax_loader_django.showFiles(input_id,upload_type);
    //    $('#'+input_id+'__submit__files').val('');
// $('#vesselModal').modal('hide');
// $('#vesselModal').modal('hide');
// $('#vesselModal').hide();
$('#vesselModal').modal("show").addClass("in");

}

if (typeof loadForm == 'function') {
  loadForm();
} else {
  console.log('no loadForm');
}

// $( "#vesselModal" ).remove();
}).fail(function(res) { //
        console.log('failed');

        $(result_output).append('<div class="error">Upload to Server Error</div>');
        $('#progress-bar-indicator').attr('class', 'progress-bar progress-bar-danger');

        var percent = '100';
        $(progress_bar_id +" .progress-bar").css("width", + percent +"%");
        $(progress_bar_id + " .status").text("0%");
        $(progress_bar_id + " .status-text").text("error");
        //submit_btn.val("Upload").prop( "disabled", false);
        });
$('#vesselModal').modal("show").addClass("in");


//	$('#vesselModal').modal({
//                   show: 'true'
  //          });

//	$('#vesselModal').modal('hide');

// $('#vesselModal').hide();

},
CloseForm: function() {
   $('#vesselModal').modal('hide');
  $('body').css({'padding-right':'0px'});	
}

}


//      }

//}
