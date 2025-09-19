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

def crispy_heading(collapse_id, header_id, heading_label):
    box_collapse_id = f"box_{collapse_id}"
    return HTML(f'''
        <div class="card-header fw-bold h4" id="{header_id}" style="padding:30px;">
            <div class="row align-items-center">
                <div class="col-6 d-flex align-items-center">
                    {heading_label}
                </div>
                <div class="col-6 text-end d-flex justify-content-end align-items-center">
                    <i class="bi fw-bold chevron-toggle down-chevron-open" style="cursor: pointer;"
                       data-bs-target="#{box_collapse_id}"
                       aria-expanded="true"
                       aria-controls="{collapse_id}"
                       style="font-size: 1.25rem; cursor: pointer;">
                    </i>
                </div>
            </div>
        </div>
    ''')

def crispy_box(collapse_id, header_id, heading_label, *field_set):
    return Div(
        crispy_heading(collapse_id, header_id, heading_label),
        Div(
            Div(
                Fieldset('', *field_set),
                css_class='card-body',
                id='box_' + collapse_id
            ),
            css_class='collapse show',
            id=collapse_id,
            role='tabpanel',
            **{'aria-labelledby': header_id}
        ),
        css_class='card mb-3',
        
    )



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
    helper.add_input(Submit(stepid, steplabel))
    return helper

def crispy_alert(message):

    return HTML("<div class=\"alert alert-danger\" role=\"alert\"><span class=\"glyphicon glyphicon-exclamation-sign\" aria-hidden=\"true\"></span><span class=\"sr-only\">Error:</span>&nbsp;&nbsp;"+message+"</div>")

def crispy_button_group(helper, buttons):
    """
    Adds a group of buttons in a single row, aligned left, with spacing.
    
    :param helper: The Crispy FormHelper instance.
    :param buttons: A list of tuples (stepid, steplabel).
    :return: Updated helper with buttons added.
    """
    button_elements = [
        Submit(stepid, steplabel, css_class='btn btn-primary')
        for stepid, steplabel in buttons
    ]

    helper.layout.append(
        Div(
            Div(
                *button_elements,
                css_class='d-flex gap-2 flex-wrap'  # Flex container for buttons
            ),
            css_class='mb-3 row'
        )
    )
    return helper

