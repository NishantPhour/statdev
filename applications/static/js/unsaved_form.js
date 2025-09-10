var django_form_checks = { 
	var: {
	     'form_changed': null,
             'href': null,
	},
        load: function() { 
	      $("form input[type=text]").change(function() { 
			      django_form_checks.var.form_changed = 'changed';
			      console.log('changed');
			      });
              $("form input[type=file]").change(function() {
                              django_form_checks.var.form_changed = 'changed';
                              console.log('changed');
                              });
              $("form textarea").change(function() {
                              django_form_checks.var.form_changed = 'changed';
                              console.log('changed');
                              });



	      $("a").click(function(e) { 
                         var href= $(this).attr('href');
                         django_form_checks.var.href = href;
                         var reg = new RegExp(/^#.*$/);
                         if (href.match(reg)) {
			 } else {
		         	if (django_form_checks.var.form_changed == 'changed') {
		//		      var success = confirm('You have unsaved changes, please click the save button to avoid losing data,  are you sure you want to navigate away from this page?'); 

    $('#myModal').modal('show')
 return false;
//  $('#myModal').modal({
//         show: 'false'
//  }); 

// return false;
//  $( function() {
//     $( "#myModal" ).dialog({
//       resizable: false,
//       height: "auto",
//       width: 400,
//       modal: true,
//       buttons: {
//         "Yes": function() {
//           window.location = href;
//           $( this ).dialog( "close" );
//         },
//         "No": function() {
//           $( this ).dialog( "close" );
//         }
//       }
//     });
//   });
//    			      if (success == false) { 
					// return false;
//				      }
				}

			}
	      });	
			 


        },
        loadUrl: function() {
          $('#myModal').modal('hide');
		window.location = django_form_checks.var.href;
	}
};

//window.onload = function () {
//	django_form_checks.load();
//}
