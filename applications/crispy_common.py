from __future__ import unicode_literals
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, HTML, Fieldset, MultiField, Div
from crispy_forms.bootstrap import FormActions
from django.conf import settings
from django.forms import Form, ModelForm, ChoiceField, FileField, CharField, Textarea, ClearableFileInput, HiddenInput, Field

"""
Purpose of this is to minimise bloating the main form.py with html and keeping the fieldset box standardise and allowing simplified changes to 
the styling of the box in one place instead of having to replicate the same style changes accross multiple fieldsets individually.  Keeping the styling standardised. 

crispy_heading: 
   crispy_heading is linked to crispy_box set h3 styling and id information.  It takes 3 parameters:

            collapse_id = Is a  unique id name for the box collaspe and uncollapse to work 
            header_id = set a id for the div.  this should be unique as well
            heading_label = This is the header/title for the collapable box. 

crispy_box: 
    crispy_box is default styling attibutues for the collapable box and takes 4 parameters, 
           collapse_id = Is a  unique id name for the box collaspe and uncollapse to work
           header_id = set a id for the div.  this should be unique as well
           heading_label = This is the header/title for the collapable box.
           *field_set = is list of fields to show in the crispy box... Utilising the self.helper.layout = Layout()
    
crispy_empty_box:
    This is just blank div to initialise and and empty object which can then be used in conjuction with crispy_box.append() the Layout Field Set boxes to.

crispy_para:
    This allow you to create a paragraph which you can than append before and after field sets.


"""

def crispy_heading(collapse_id, header_id , heading_label):
    #    return Div(id=header_id, css_class='panel-heading')
     return Div(HTML('<h3 class="panel-title" ><a role="button" data-toggle="collapse" href="#'+collapse_id+'" aria-expanded="false" aria-controls="application_collapse"><span class="glyphicon glyphicon-chevron-down collapse-glyph"></span></span>'+heading_label+' </a></h3>'), id=header_id, css_class='panel-heading')

def crispy_box(collapse_id, header_id , heading_label,*field_set):
     return Div(crispy_heading(collapse_id, header_id, heading_label),
                            Div(Div(
                              Fieldset('',
                                   *field_set
                            ), css_class='panel-body',
                          ), css_class="panel-collapse collapse in",id=collapse_id,
                    ), css_class='panel panel-default'
             ,id='box_'+collapse_id)

def crispy_empty_box():
    return Div()

def crispy_para(paragraph):
    return HTML("<div class='form-group'><label class='control-label col-xs-12 col-sm-4 col-md-3 col-lg-2'></label><div class='controls col-xs-12 col-sm-8 col-md-6 col-lg-4'><strong>"+paragraph+"</strong></div></div>")

def crispy_para_red(paragraph):
    return HTML("<div class='form-group'><label class='control-label col-xs-12 col-sm-4 col-md-3 col-lg-2'></label><div class='controls col-xs-12 col-sm-8 col-md-6 col-lg-4 alert-danger'><strong class='bs-callout-danger'>"+paragraph+"</strong></div></div>")

def crispy_para_with_label(label,paragraph):
    return HTML("<div class='form-group'><label class='control-label col-xs-12 col-sm-4 col-md-3 col-lg-2'>"+label+"</label><div class='controls col-xs-12 col-sm-8 col-md-6 col-lg-4'>"+paragraph+"</div></div>")

def crispy_para_no_label(paragraph):
    return HTML("<div class='form-group'><div class='controls col-xs-12 col-sm-8 col-md-6 col-lg-4'><strong>"+paragraph+"</strong></div></div>")

def crispy_h1(paragraph):
    return HTML("<div class='form-group'><div class='controls col-xs-12 col-sm-8 col-md-6 col-lg-4'><h1>"+paragraph+"</h1></div></div>")

def crispy_h2(paragraph):
    return HTML("<div class='form-group'><div class='controls col-xs-12 col-sm-8 col-md-6 col-lg-4'><h2>"+paragraph+"</h2></div></div>")

def crispy_h3(paragraph):
    return HTML("<div class='form-group'><div class='controls col-xs-12 col-sm-8 col-md-6 col-lg-4'><h3>"+paragraph+"</h3></div></div>")

def crispy_h4(paragraph):
    return HTML("<div class='form-group'><div class='controls col-xs-12 col-sm-8 col-md-6 col-lg-4'><h4>"+paragraph+"</h4></div></div>")

def crispy_h5(paragraph):
    return HTML("<div class='form-group'><div class='controls col-xs-12 col-sm-8 col-md-6 col-lg-4'><h5>"+paragraph+"</h5></div></div>")

def crispy_h6(paragraph):
    return HTML("<div class='form-group'><div class='controls col-xs-12 col-sm-8 col-md-6 col-lg-4'><h6>"+paragraph+"</h6></div></div>")

def crispy_h7(paragraph):
    return HTML("<div class='form-group'><div class='controls col-xs-12 col-sm-8 col-md-6 col-lg-4'><h7>"+paragraph+"</h7></div></div>")

def crispy_button_link(label,link):
    return HTML("<div class='form-group'><label class='control-label col-xs-12 col-sm-4 col-md-3 col-lg-2'></label><div class='controls col-xs-12 col-sm-8 col-md-6 col-lg-4'><a class='btn btn-primary btn-sm' role='button' href='"+link+"'>"+label+"</a></div></div>")

#TODO check this: is this correct? 
def check_fields_exist(fields,fieldstocheck):
    for fe in fieldstocheck:
        if fe in fields:
            return True
    return False

def crispy_button(helper,stepid,steplabel):
    helper.add_input(Submit(stepid, steplabel, css_class='btn-lg'))
    return helper

def crispy_alert(message):

    return HTML("<div class=\"alert alert-danger\" role=\"alert\"><span class=\"glyphicon glyphicon-exclamation-sign\" aria-hidden=\"true\"></span><span class=\"sr-only\">Error:</span>&nbsp;&nbsp;"+message+"</div>")
