# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from .models import Location, Record, PublicationNewspaper, PublicationWebsite, PublicationFeedback,Referral,Application, Delegate, Compliance, Condition
from django.utils.safestring import SafeText
from django.contrib.auth.models import Group
from django.db.models import Q
from applications.email import sendHtmlEmail, emailGroup, emailApplicationReferrals
from fpdf import FPDF
import textwrap
import os
from ledger_api_client.managed_models import SystemUser, SystemUserAddress

class PDF(FPDF):
    def header(self):
        # Select Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Move to the right
        self.cell(80)
        # Framed title
        self.cell(30, 10, 'Title', 1, 0, 'C')
        # Line break
        # self.ln(20)

class PDFtool(FPDF):

    bullet_number_count = int(1)
    def header(self):
        # Select Arial bold 15
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
        self.image(BASE_DIR+'/applications/static/images/swan_canning_riverpark_dbca.png', 30, 7, 144,24)
        self.set_font('Arial', 'B', 15)
        # Move to the right
        self.cell(80)
        # Framed title
        #self.cell(30, 10, 'Title', 1, 0, 'C')
        # Line break
        self.ln(25)
#    fdpf.header()

    def footer(self):
        """
        Footer on each page
        """
        # position footer at 15mm from the bottom
        self.set_y(-15)

        # set the font, I=italic
        self.set_font("Arial", "I", 8)

        # display the page number and center it
        pageNum = "Page %s/{nb}" % self.page_no()
        self.cell(0, 10, pageNum, "C")

    def create_para(self,pdf,text):
        para_split =  textwrap.wrap(text, 116)
        for p in para_split:
            pdf.cell(0, 5, p ,0,1,'L')
        return pdf

    def horizontal_line(self,pdf):
#       pdf.line(7, 110, 205, 110)
        current_font_family = pdf.font_family
        current_font_size = pdf.font_size_pt
        current_font_style = pdf.font_style
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 1,'_____________________________________________________________' ,0,1,'L')
        pdf.cell(0, 4, ' ' ,0,1,'L')
        pdf.set_font(current_font_family,current_font_style,current_font_size)
        return pdf

    def heading1_bold(self,pdf,text):
        current_font_family = pdf.font_family
        current_font_size = pdf.font_size_pt
        current_font_style = pdf.font_style
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 7, text,0,1,'L')
        pdf.set_font(current_font_family,current_font_style,current_font_size)
        return pdf

    def heading2_bold(self,pdf,text):
        current_font_family = pdf.font_family
        current_font_size = pdf.font_size_pt
        current_font_style = pdf.font_style
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 7, text,0,1,'L')
        pdf.set_font(current_font_family,current_font_style,current_font_size)
        return pdf

    def column_para(self,pdf,column1,column2,column1width):

        if column1width is None:
           column1width = 80
#        if len(column2) == 0:
#            column2 = 'iiii '
        loop = 1
        para_split =  textwrap.wrap(column2, 118 - column1width)

#        pdf.cell(6, 5, ' ',0,0,'L')
#        pdf.cell(column1width, 5, column1 ,0,0,'L')

        if len(column2) == 0:
            pdf.cell(6, 5, ' ',0,0,'L')
            pdf.cell(column1width, 5, column1 ,0,0,'L')
            pdf.cell(6, 5, ':',0,0,'L')
            pdf.cell(6, 5, ' ' ,0,1,'L')
        else:
            for p in para_split:
                if loop > 1:
                    pdf.cell(6, 5, ' ',0,0,'L')
                    pdf.cell(column1width, 5, column1 ,0,0,'L')
                    pdf.cell(6, 5, ':',0,0,'L')
                    pdf.cell(6, 5, p ,0,1,'L')
                else:
                    pdf.cell(6, 5, ' ',0,0,'L')
                    pdf.cell(column1width, 5, column1 ,0,0,'L')
                    pdf.cell(6, 5, ':',0,0,'L')
                    pdf.cell(6, 5, p ,0,1,'L')
                loop = loop + 1
        #    pdf.cell(6, 5, '  ' ,0,1,'L')

        return pdf

    def column_para_no_seperator(self,pdf,column1,column2,column1width,indent):
        if column1width is None:
           column1width = 80
        if indent is None:
           indent = 1
        loop = 1
        para_split =  textwrap.wrap(column2, 118 - column1width - (indent * 5) )
        for p in para_split:

            indentloop = 0
            while indentloop < indent:
                pdf.cell(6, 5, ' ',0,0,'L')
                indentloop = indentloop + 1

            if loop > 1:
                indentloop = 0
                
#                pdf.cell(6, 5, ' ',0,0,'L')
                pdf.cell(column1width, 5, ' ' ,0,0,'L')
                pdf.cell(6, 5, p ,0,1,'L')
            else:
 #               pdf.cell(6, 5, ' ',0,0,'L')
                pdf.cell(column1width, 5, column1 ,0,0,'L')
                pdf.cell(6, 5, p ,0,1,'L')
            loop = loop + 1

    
#        pdf.cell(6, 5, ' ',0,0,'L')
 #       pdf.cell(column1width, 5, column1 ,0,0,'L')
  #      pdf.cell(6, 5, column2 ,0,1,'L')
        return pdf

    def column_para_flexi(self,pdf,column1,column2,column1width,column1fs='',column2fs=''):
        if column1width is None:
           column1width = 60
        current_font_family = pdf.font_family
        current_font_size = pdf.font_size_pt
        current_font_style = pdf.font_style

        loop = 1
        para_split =  textwrap.wrap(column2, 118 - column1width)
        for p in para_split:

            if loop > 1:
                pdf.set_font('Arial', column1fs, current_font_size)
                pdf.cell(6, 5, ' ',0,0,'L')
                pdf.cell(column1width, 5, ' ' ,0,0,'L')
                pdf.cell(6, 5, ' ',0,0,'L')
                pdf.set_font(current_font_family,column2fs,current_font_size)
                pdf.cell(6, 5, p ,0,1,'L')
            else:
                pdf.set_font('Arial', '', current_font_size)
                pdf.cell(6, 5, ' ',0,0,'L')
                pdf.cell(column1width, 5, column1 ,0,0,'L')
                pdf.cell(6, 5, ':',0,0,'L')
                pdf.set_font(current_font_family,column2fs,current_font_size)
                pdf.cell(6, 5, p ,0,1,'L')
            loop = loop + 1

        pdf.set_font(current_font_family,current_font_style,current_font_size)
        return pdf


    def column_para_bold(self,pdf,column1,column2,column1width):
        if column1width is None:
           column1width = 80
        current_font_family = pdf.font_family
        current_font_size = pdf.font_size_pt
        current_font_style = pdf.font_style
 
        loop = 1
        para_split =  textwrap.wrap(column2, 118 - column1width)
        for p in para_split:
            
            if loop > 1:
                pdf.set_font('Arial', 'B', current_font_size)
                pdf.cell(6, 5, ' ',0,0,'L')
                pdf.cell(column1width, 5, ' ' ,0,0,'L')
                pdf.set_font(current_font_family,'I',current_font_size)
                pdf.cell(6, 5, p ,0,1,'L')
            else: 
                pdf.set_font('Arial', 'B', current_font_size)
                pdf.cell(6, 5, ' ',0,0,'L')
                pdf.cell(column1width, 5, column1 ,0,0,'L')
                pdf.set_font(current_font_family,'I',current_font_size)
                pdf.cell(6, 5, p ,0,1,'L')
            loop = loop + 1

        pdf.set_font(current_font_family,current_font_style,current_font_size)
        return pdf

    def bullet_numbers_para(self,pdf,text):
        loop = 1
        pdf.cell(0,5,' ', 0,1,'L')

        para_split =  textwrap.wrap(text, 110)
        for p in para_split:
            if loop > 1:
                pdf.cell(10, 5, ' ',0,0,'L')
                pdf.cell(60, 5, p ,0,1,'L')
            else:
                pdf.cell(10, 5, str(self.bullet_number_count)+'.',0,0,'L')
                pdf.cell(60, 5, p ,0,1,'L')
            loop = loop + 1

        self.bullet_number_count = self.bullet_number_count + 1
        return pdf

    def pre_text_bold_para(self,pdf,boldtext,normaltext):
        pdf.cell(0,5,' ', 0,1,'L')

    def space(self,pdf):
        pdf.cell(0,5,' ', 0,1,'L')
        return pdf

    def generate_licence(self,app):
#         pdf = FPDF('P', 'mm', 'A4')
         pdf = PDFtool('P', 'mm', 'A4')
         pdf.alias_nb_pages()
         pdf.add_page()
         # pdf.image('plugins/flightsensation/images/flight_voucher.jpg', 0, 0, 210,297)

         #swan_canning_riverpark_dbca.png
         #pdf.image('applications/static/images/swan_canning_riverpark_dbca.png', 30, 7, 144,24)

         pdf.set_font('Arial', 'I', 10)
#         pdf.cell(0,28,' ', 0,1,'L')

         pdf = self.create_para(pdf,'Pursuant to Section 32 of the Swan and Canning Rivers Management Act 2006 and Part 4 (Regulation 29) of the Swan and Canning Rivers Management Regulations 2007, this is to certify that a licence and permit are issued to the person(s) or organisation described hereunder as licence and permit holder and that person(s) or organisation is permitted to carry out the authorised acts or activities for the duration specified subject to the conditions listed below.')
 #        pdf.set_font('Arial', 'B', 16)
         #print pdf.font_family
          #rint pdf.font_size_pt
         #print pdf.font_size_pt

        # from pprint import pprint
#         pprint(vars(pdf))
  #       pdf.cell(0, 1,'_____________________________________________________________' ,0,1,'L')

         pdf.set_font('Arial', '', 10)
         pdf = self.horizontal_line(pdf)
         #TODO check this
         if app.organisation: 
             holder_name = app.organisation.name 
         else:
             applicant = SystemUser.objects.get(ledger_id=app.applicant)
             holder_name = applicant.legal_first_name + ' ' + applicant.legal_last_name


         pdf = self.column_para(pdf,'Licence/Permit holder',holder_name,None)
         # group spacer
         pdf = self.space(pdf)
         pdf = self.column_para(pdf,'Authorised works, acts or activities',app.title,None)
         pdf = self.space(pdf)
         pdf = self.column_para(pdf,'Location of works, acts or activities','',None)
         pdf = self.space(pdf)
         pdf = self.column_para(pdf,'Approval date', app.start_date.strftime("%d %b %Y"),None)
         pdf = self.space(pdf)
         pdf = self.column_para(pdf,'Expiry date', app.expiry_date.strftime("%d %b %Y"),None)
         pdf = self.space(pdf)
         pdf = self.column_para(pdf,'Vessel details','',None)

         vessel_count = 0
         for v in app.application.vessels.all():
             vessel_count = vessel_count + 1
             if v.vessel_type == 0:
                 pdf = self.column_para_no_seperator(pdf,str(vessel_count)+'.',v.get_vessel_type_display()+' - Name : '+v.name+ ', Vessel ID : '+v.vessel_id+', size(m) : '+str(v.size)+' engine(kw) : '+str(v.engine)+' Passenger capacity : '+str(v.passenger_capacity),10,1.5)
             if v.vessel_type == 1:
                 pdf = self.column_para_no_seperator(pdf,str(vessel_count)+'.',v.get_vessel_type_display()+' - '+v.craft_type+' (max:'+str(v.number_of_crafts)+')',10,1.5)
    #vessel_type = models.SmallIntegerField(choices=VESSEL_TYPE_CHOICES, null=True, blank=True)
    ## Vessel Information
    #name = models.CharField(max_length=256)
    #vessel_id = models.CharField(max_length=256, null=True, blank=True, verbose_name='Vessel identification')
    #registration = models.ManyToManyField(Record, blank=True, related_name='vessel_documents')
    #size = models.PositiveIntegerField(null=True, blank=True, verbose_name='size (m)')
    #engine = models.PositiveIntegerField(null=True, blank=True, verbose_name='engine (kW)')
    #passenger_capacity = models.PositiveIntegerField(null=True, blank=True)
    ## craft Information
    #craft_type = models.CharField(max_length=256, null=True, blank=True, verbose_name='Craft Type')
    #number_of_crafts = models.PositiveIntegerField(null=True, blank=True, verbose_name='Number of crafts')
    #documents = models.ManyToManyField(Record, blank=True, related_name='craft_documents')


         pdf = self.space(pdf)
     

         pdf = self.horizontal_line(pdf)

         pdf = self.heading1_bold(pdf,'PERMIT LICENCE '+str(app.id))

         # Conditions and advise

         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.set_font('Arial', 'B', 9)
         pdf.cell(60, 5, 'CONDITIONS TO APPLICANT',0,1,'L')
         pdf.set_font('Arial', '', 9)

         application_condition = Condition.objects.filter(application=app.application).order_by('condition_no')

         condition_count = 1
         for c in application_condition:
              #condition
              if len(c.condition) > 0 and c.condition_no > 0:
                  pdf = self.column_para_no_seperator(pdf,str(c.condition_no)+'.', c.condition,10,1)
                  pdf = self.space(pdf)
                  condition_count = condition_count + 1


         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.set_font('Arial', 'B', 9)
         pdf.cell(60, 5, 'ADVISE TO APPLICANT',0,1,'L')
         pdf.set_font('Arial', '', 9)

         application_condition = Condition.objects.filter(application=app.application).order_by('advise_no')

         condition_count = 1
         for c in application_condition:

              if c.advise_no is None:
                  c.advise_no = 0

              #advise
              if len(c.advise) > 0 and c.advise_no:
                  pdf = self.column_para_no_seperator(pdf,str(c.advise_no)+'.', c.advise,10,1)
                  pdf = self.space(pdf)
                  condition_count = condition_count + 1


         # end of conditins and advise






         #pdf = self.heading2_bold(pdf,'CONDITION(S)')
         #pdf = self.bullet_numbers_para(pdf,'Whilst operating within the Swan Canning Riverpark, a copy of this approval shall remain with this operation at all times, and must be shown to a government inspector on demand.')
         #pdf = self.bullet_numbers_para(pdf,'The Operator shall abide by the Specific Licence Conditions and General Licence Conditions of Licence L'+str(app.id)+' (refer below).')
         #pdf = self.bullet_numbers_para(pdf,'The Operator does not have priority access over other users to any area of the Swan Canning Development Control Area.')
         #pdf = self.bullet_numbers_para(pdf,'The Operator shall not erect any structures (including signage) or store any equipment associated with the operation within the Swan Canning Development Control Area.')
         #pdf = self.bullet_numbers_para(pdf,'The Operator shall ensure that no damage to the riverbed, foreshore or vegetation within the Swan Canning Development Control Area occurs as a result of the Operation.  The Operator shall make good any damage to the river and/or foreshore area, to the satisfaction of the Department.')
         #pdf = self.bullet_numbers_para(pdf,'The Operator shall ensure that no damage to the riverbed, foreshore or vegetation within the Swan Canning Development Control Area occurs as a result of the Operation.  The Operator shall make good any damage to the river and/or foreshore area, to the satisfaction of the Department.')
         #pdf = self.bullet_numbers_para(pdf,'Refuelling within the River reserve shall be undertaken at a licensed refuelling facility and by a person with a coxswain\'s certificate, or higher maritime qualification.')
         #pdf = self.bullet_numbers_para(pdf,'The Operator shall ensure that no sewage, greywater, fuel, garbage or other solid or liquid waste material enters the River reserve as a result of the operation.')
         #pdf = self.bullet_numbers_para(pdf,'The Operator shall have sullage tanks installed and operational in the vessel.')
         #pdf = self.bullet_numbers_para(pdf,'General waste and refuse generated aboard the vessel must not be disposed of by use of public bins installed at jetties, parks or other locations, including commercial bins at East Street Jetty and Barrack Street Jetty (unless by prior arrangement with the relevant authority).')
         #pdf = self.bullet_numbers_para(pdf,'The Operator\'s vessel shall not anchor in any area that may cause restrictions to navigating traffic or secure the Operator\'s vessel to any mooring buoy that is not lawful to use.')
         #pdf = self.bullet_numbers_para(pdf,'The Operator shall not create undue noise or nuisance through its Operations.')
         #pdf = self.bullet_numbers_para(pdf,'The Operator\'s vessel shall not enter any gazetted marine park within the Swan River without lawful authority pursuant to the Conservation and Land Management Regulations 2002 from the Department.')
         #pdf = self.bullet_numbers_para(pdf,'The Operator shall not transit through the Narrows Personal Watercraft Area.')
         #pdf = self.bullet_numbers_para(pdf,'The Operator shall obtain all relevant approvals from other government authorities (e.g. relevant local government authorities, and Department of Transport) that may be required, including the permission to berth at any public jetties, and if requested by the Department, supply copies of such approvals to the Director of the Rivers and Estuaries Division.')

         #pdf = self.create_para(pdf,'<<Other conditions to follow here>>')
         #pdf = self.create_para(pdf,'<<Advice to Applicant>>')
         pdf = self.heading2_bold(pdf,'DEFINITIONS')
     
         pdf = self.column_para_bold(pdf,'Act','means the Swan and Canning Rivers Management Act 2006.',30)
         pdf = self.column_para_bold(pdf,'Department','means the Department of Biodiversity, Conservation and Attractions.',30)
         pdf = self.column_para_bold(pdf,'Director General','means the chief executive officer (CEO) of the Department (the department assisting the Minister in the administration of the Act) or a delegate of the CEO.',30)
         pdf = self.column_para_bold(pdf,'Operations','means the commercial operations which may be undertaken by an operator pursuant to the licence.',30)
         pdf = self.column_para_bold(pdf,'Operator','means a person (includes incorporated bodies) who holds a licence.',30)
         pdf = self.column_para_bold(pdf,'Regulations', 'means the Swan and Canning Rivers Management Regulations 2007.',30)
         pdf = self.column_para_bold(pdf,'River reserve', 'means the reserve over the Swan and Canning rivers defined in section 11(2) and described in Schedule 4 of the Act.',30)


         pdf = self.heading2_bold(pdf,'INTERPRETATION')
         pdf = self.column_para_no_seperator(pdf,'a.', 'A reference to anything that the Operator must or must not do includes, where the context permits, the Operator\'s employees, agents, and contractors.',10,1)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'b.', 'The singular includes the plural and vice versa.',10,1)
         pdf = self.space(pdf)

         pdf = self.column_para_no_seperator(pdf,'c.', 'A reference to any thing is a reference to the whole or any part of it and a reference to a group of things or persons is a reference to any one or more of them.',10,1)
         pdf = self.space(pdf)

         pdf = self.column_para_no_seperator(pdf,'d.', 'If the Operator consists of a partnership or joint venture, then:',10,1)
         pdf = self.space(pdf)

         pdf = self.column_para_no_seperator(pdf,'i.', 'an obligation imposed on the Operator binds each person who comprises the Operator jointly and severally;',10,3)
         pdf = self.space(pdf)

         pdf = self.column_para_no_seperator(pdf,'e.', 'A reference to a statute, ordinance, code or other law includes regulations and other instruments under it and consolidations, amendments, re-enactments or replacements of any of them',10,1)
         pdf = self.space(pdf)

         pdf = self.column_para_no_seperator(pdf,'f.', 'If a word or phrase is defined, other grammatical forms of that word or phrase have a corresponding meaning.',10,1)
         pdf = self.space(pdf)

         pdf = self.column_para_no_seperator(pdf,'g.', 'If the word "including" or "includes" is used, the words "without limitation" are taken to immediately follow.',10,1)
         pdf = self.space(pdf)

         pdf = self.heading2_bold(pdf,'GENERAL LICENCE CONDITIONS')
         pdf = self.column_para_no_seperator(pdf,'1.', 'Compliance with laws',10,1)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'  ', 'Conditions in this section apply to all commercial Operators operating on the Swan and Canning Rivers River reserve defined in section 11(2) and Schedule 4 under the Act.',10,1)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(a)', 'The Operator shall comply with all laws relating to the conduct of the Operations, including but not limited to:',10,3)
         pdf = self.column_para_no_seperator(pdf,'(i)', 'The Act',10,5)
         pdf = self.column_para_no_seperator(pdf,'(ii)', 'The Regulations',10,5)
         pdf = self.column_para_no_seperator(pdf,'(iii)', 'The Conservation and Land Management Act 1984',10,5)
         pdf = self.column_para_no_seperator(pdf,'(iv)', 'The Conservation and Land Management Regulations 2002',10,5)
         pdf = self.column_para_no_seperator(pdf,'(v)', 'The Wildlife Conservation Act 1950',10,5)
         pdf = self.column_para_no_seperator(pdf,'(vi)', 'The Wildlife Conservation Regulations 1970',10,5)
         pdf = self.column_para_no_seperator(pdf,'(vii)', 'any other Act, Regulation or local laws',10,5)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(b)', 'The Operator shall arrange, pay for and maintain during the term of the licence all licences, certificates and authorities required by the Director General for the operation of the licence and shall present them to the Director General if requested.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'2.', 'Risk and safety',10,1)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(a)', 'The Operator agrees to conduct Operations entirely at the Operator\'s own risk and the Operator shall inform itself, its employees, agents and contractors in either a written or oral form in a language understood by regarding the risks and dangers arising from the Operations that are likely to be encountered on the River reserve.',10,3)
         pdf = self.column_para_no_seperator(pdf,'(b)', 'The Operator shall carry appropriate safety and first aid equipment at all times while on the River reserve.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(c)', 'The Operator shall ensure that appropriate risk management systems, strategies and procedures are in place to minimise foreseeable risks to the environment, the values of the River reserve, the Operator\'s employees, agents or contractors or other members of the public, and shall produce evidence of such systems, strategies and procedures if requested by the Director General.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'3.', 'Property damage and injury',10,1)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(a)', 'The Operator shall report to the Department full details of any damage to the Department\'s property caused by the Operator or any of its passengers while on the River reserve within forty-eight (48) hours of the occurrence of the damage.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(b)', 'The Operator shall report any incident in which the safety of any of its employees, agents and contractors were at risk, or where emergency services were contacted in the course of conducting Operations on the River reserve. Using the prescribed Commercial Operator Incident Report form, the Operator shall submit a report on all such incidents to the Department within forty-eight (48) hours of such incident/s occurring.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(c)', 'In the event of any incident occurring on the River reserve involving the Operator, the Operator\'s employees, agents and contractors that results in a fatality, or injury to any person that requires medical attention from a Doctor, medical facility or hospital, the Operator must immediately complete the prescribed Commercial Operator Incident Report form and submit it to the Department within forty-eight (48) hours of the incident occurring. If the Operator was not present at the time of the incident, the Operator shall require each of its employees who were involved in or observed the incident to provide the Operator with supporting reports on the incident, using the Commercial Operator Incident Report form, and the Operator shall submit these supporting incident reports along with his own incident report to the Department within forty-eight (48) hours of the incident occurring. The Commercial Operator Incident Report form can be found on the Department\'s commercial operations licensing web page under Industry Documents.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(d)', 'The Operator agrees that neither the state, Department, nor the Director General take any responsibility or liability for the security, loss, damage or otherwise of any vehicle, vessel, machinery, equipment or other goods or property owned by, or under the control of, the Operator.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'4.', 'Employees, agents and contractors',10,1)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(a)', 'The Operator shall:',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(i)', 'only employ or engage competent and qualified employees, agents and contractors in relation to the Operations;',10,5)
         pdf = self.column_para_no_seperator(pdf,'(ii)', 'fully inform all employees, agents and contractors employed or engaged in relation to the Operations of the terms of the licence and these conditions relevant to the Operations and any other conditions or restrictions applied to the licence; and',10,5)
         pdf = self.column_para_no_seperator(pdf,'(iii)', 'ensure that all employees, agents and contractors employed or engaged in relation to the Operations of the licence comply with the terms of the licence, these conditions and any other conditions or restrictions relevant to the Operations.' ,10,5)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(b)', 'In accepting the licence, the Operator agrees that a breach by any employee, agent or contractor of the Operator of any of the terms, conditions or restrictions imposed upon the licence shall constitute a breach by the Operator and that the Operator shall be vicariously liable for such breaches.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(c)', 'Without the written approval of the Director General, an Operator shall not employ or engage an employee, agent or contractor for Operations on the River reserve that has been convicted in the past 10 years of:',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(i)', 'an offence under the Act',10,5)
         pdf = self.column_para_no_seperator(pdf,'(ii)', 'an offence under the Regulations',10,5)
         pdf = self.column_para_no_seperator(pdf,'(iii)', 'an offence under the Conservation and Land Management Act 1984 carrying a penalty of $400 or greater',10,5)
         pdf = self.column_para_no_seperator(pdf,'(iv)', 'an offence under the Conservation and Land Management Regulations 2002 carrying a penalty of $200 or greater',10,5)
         pdf = self.column_para_no_seperator(pdf,'(v)', 'an offence under the Wildlife Conservation Act 1950 carrying a penalty of $4000 or greater',10,5)
         pdf = self.column_para_no_seperator(pdf,'(vi)', 'an offence under the Wildlife Conservation Regulations 1970 carrying a penalty of $2000.',10,5)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'5.', 'Access, records and reports',10,1)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(a)', 'The Operator shall prepare, keep and preserve a full record of Operations and, if requested in writing by the Director General, such records shall be set out in a form determined by the Director General.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(b)', 'If requested by the Director General or an Inspector, the Operator shall make available access on the Operator\'s vessel for any Departmental officer for the purpose of observing the conduct of Operations.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(c)', 'The Operator shall immediately report to the Department any outbreak of fire in the vicinity of the Operator\'s Operations.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'6.', 'Dealings with the River reserve',10,1)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(a)', 'The Operator shall, in respect of the River reserve:',10,3)
         pdf = self.column_para_no_seperator(pdf,'(i)', 'ensure all rubbish arising from the Operations is removed from the site of the Operations prior to departure;',10,5)
         pdf = self.column_para_no_seperator(pdf,'(ii)', 'ensure vegetation and animals are not damaged or disturbed;',10,5)
         pdf = self.column_para_no_seperator(pdf,'(iii)', 'ensure the Operations do not disrupt other persons and activities;',10,5)
         pdf = self.column_para_no_seperator(pdf,'(iv)', 'ensure that anchoring occurs at un-vegetated areas of seabed (sand and mud) and at a safe distance from sensitive habitats (e.g. seagrass), so as not to cause any environmental damage (except in an emergency);',10,5)
         pdf = self.column_para_no_seperator(pdf,'(v)', 'ensure that passengers only embark and disembark vessels at locations stipulated in the application, or otherwise approved by the Department\'s officers (except in an emergency); and',10,5)
         pdf = self.column_para_no_seperator(pdf,'(vi)', 'ensure that launching only occurs at designated launching sites as stipulated in the application.',10,5)
#
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(b)', 'The Operator shall not, in respect of the River reserve:',10,3)
         pdf = self.column_para_no_seperator(pdf,'(i)', 'bring or allow any person to bring animals, unless prior authorisation has been obtained;',10,5)
         pdf = self.column_para_no_seperator(pdf,'(ii)', 'bring or allow any person to bring a firearm onto the River reserve, unless authorised by special endorsement on the Operator\'s licence;',10,5)
         pdf = self.column_para_no_seperator(pdf,'(iii)', 'erect or cause to be erected any water-based structures (including inflatable equipment) without approval from the Department;',10,5)
         pdf = self.column_para_no_seperator(pdf,'(iv)', 'impede public access to and on the River reserve;',10,5)
         pdf = self.column_para_no_seperator(pdf,'(v)', 'construct or authorise the construction of any structure (including beach, swing moorings, pontoons) within the River reserve without the prior approval of the Department and/or Department of Transport.',10,5)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'7.', 'Publicity and marketing',10,1)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(a)', 'The Operator shall not promote the Operations or display any other advertising material in the Swan Canning Riverpark, as defined in section 9 and described in Schedule 2 of the Act, except with the prior written consent of the Director General.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(b)', 'If the Director General is of the opinion that any document used by the Operator in the promotion or marketing of the Operations is inappropriate or is in any way inconsistent with the terms of the licence, the Director General may direct the Operator to cease using such document.', 10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(c)', 'If the Director General directs the Operator to cease using any document under condition 7(b), the Operator shall promptly comply with such direction and provide such evidence as the Director General may require to demonstrate the Operator\'s compliance.', 10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(d)', 'The Operator shall actively promote the recreation and conservation values of the River reserve that are the subject of the Operations.', 10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(d)', 'The Operator shall, if requested by the Director General, attend training workshops relating to the values and management of the River reserve.', 10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(e)', 'The Operator shall ensure that staff present themselves in accordance with customer service standards expected by the Director General for all licensed activities that occur in the River reserve. Minimum standards include the provision of:', 10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(f)', 'The Operator shall ensure that staff present themselves in accordance with customer service standards expected by the Director General for all licensed activities that occur in the River reserve. Minimum standards include the provision of:', 10,3)
         pdf = self.column_para_no_seperator(pdf,'(i)', 'positive, courteous and friendly service;',10,5)
         pdf = self.column_para_no_seperator(pdf,'(ii)', 'competent and efficient assistance;',10,5)
         pdf = self.column_para_no_seperator(pdf,'(iii)', 'timely and accurate information; and',10,5)
         pdf = self.column_para_no_seperator(pdf,'(iv)', 'safe and pleasant conditions for clients.',10,5)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf, '8.', 'Indemnity',10,1)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(a)', 'The Operator agrees to indemnify the Director General from and against liability for all actions, suits, demands, costs, losses, damages and expenses (claims) (e.g. search and rescue costs) that may be brought against or made upon the Director General caused by or arising in any way out of the conduct of:',10,3)
         pdf = self.column_para_no_seperator(pdf,'(i)', 'the Operator;',10,5)
         pdf = self.column_para_no_seperator(pdf,'(ii)', 'the Operator\'s employees, agents or contractors.',10,5)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf, '9.', 'Insurance',10,1)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(a)', 'The Operator shall, at all times during the period of the licence, maintain a policy of public liability insurance that covers the areas and Operations allowed under the licence in the name of the Operator to the extent of its rights and interests for a sum of not less than $10 million per event.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(b)', 'The Operator shall provide the Director General proof of the existence and currency of such insurance policy whenever requested by the Director General during the term of the licence.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(c)', 'The Operator shall pay all premiums of the public liability insurance policy when they are due, comply with all of the terms of that policy and shall make the insurer aware of the licence, these conditions and the indemnity given to the Director General.',10,3)
         pdf = self.column_para_no_seperator(pdf, '10.', 'Notice of default',10,1)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(a)', 'If the Operator fails to comply with any of these conditions or any other condition of the licence, the Director General may, by notice to the Operator, require the Operator to remedy such failure within a reasonable time.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(b)', 'If the Operator fails to comply with the notice within the time specified, the Director General may immediately cancel or suspend the licence.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(c)', 'Any notice to the Operator shall be in writing and may be served upon the Operator by addressing it to the Operator and posting it to, or leaving it at, the address registered with the Department.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf, '11.', 'Rights reserved',10,1)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(a)', 'Without limiting the rights of the Director General, the Director General reserves the right to add to, cancel, suspend and otherwise vary the terms and conditions of the licence at any time in accord with section 32(4) of the Act.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(b)', 'The expiry, cancellation or termination of the licence (whether under the Act or arising from a breach by the Operator) does not affect any rights the Director General may have in relation to the Operator resulting from anything that occurred before the expiry, cancellation or termination of the licence.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(c)', 'In circumstances where licence numbers are limited, the Director General reserves the right to suspend, cancel or refuse to renew the licence if the licence is not used to a reasonable extent as determined by the Director General. In all cases, the Operator shall ensure that the licence is not held inactive.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(d)', 'The Operator acknowledges and accepts the Department may at any time restrict the license holder\'s access to an area due to environmental, safety or management concerns.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(e)', 'The Operator acknowledges and accepts that the Department reserves the right to limit the number of licences offering any activities within the River reserve. In this event, the selection of licence holders may be through an Expression of Interest process and the prospective licence holders would be required to apply.',10,3)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(f)', 'The Operator acknowledges and accepts that in the event that the licence activity causes undue interference or disturbance to other River reserve visitors, the Department reserves the right to:',10,3)
         pdf = self.column_para_no_seperator(pdf,'(i)', 'add, delete or alter any conditions endorsed upon, or attached to, the licence approval;',10,5)
         pdf = self.column_para_no_seperator(pdf,'(ii)', 'suspend the licence; or',10,5)
         pdf = self.column_para_no_seperator(pdf,'(iii)', 'cancel the licence.',10,5)
         pdf = self.space(pdf)

         pdf = self.column_para_no_seperator(pdf, '12.', 'Limitation of licence',10,1)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf,'(a)', 'The Operator acknowledges and accepts that:',10,3)
         pdf = self.column_para_no_seperator(pdf,'(i)', 'the licence does not give the Operator priority or exclusive rights to access the River reserve or exclusive rights to conduct the Operations;',10,3)
         pdf = self.column_para_no_seperator(pdf,'(ii)', 'the Operator shall ensure that all other necessary approvals required for the conduct of the Operations are obtained and presented to the Director General, if required;',10,3)
         pdf = self.column_para_no_seperator(pdf,'(iii)', 'the licence does not authorise the Operator to use land other than the River reserve;',10,3)
         pdf = self.column_para_no_seperator(pdf,'(iv)', 'the Operator shall ensure that all the necessary approvals or permission required from lessees/owners of properties other than the Department are obtained before using roads/tracks/ facilities on their properties or leased areas;',10,3)
         pdf = self.column_para_no_seperator(pdf,'(v)', 'at the expiry of the original term of the licence, the Department may conduct a competitive process to determine who will be granted licences. Licence numbers may be limited for a particular activity or area;',10,3)
         pdf = self.column_para_no_seperator(pdf,'(vi)', 'if the licence is not renewed, the operator is responsible, at his/her expense, for the removal of all structures and utilities associated with the operation and restoration of the area (as applicable), to the satisfaction of the Director General.',10,3)

         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf, '13.', 'No agency',10,1)
         pdf = self.space(pdf)
 
         pdf = self.column_para_no_seperator(pdf, '(a)', 'The Operator acknowledges that nothing in the licence may be construed to make either the Operator or the Director General a partner, agent, employee or joint venturer of the other. ',10, 3)

         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf, '14.', 'No assignment or transfer',10,1)
         pdf = self.space(pdf)
         pdf = self.column_para_no_seperator(pdf, '(a)', 'The Operator shall not:', 10,3)
         pdf = self.column_para_no_seperator(pdf, '(i)', 'sell, transfer, assign, mortgage, charge or otherwise dispose of or deal with any of its rights or obligations under the licence;', 10,5)
         pdf = self.column_para_no_seperator(pdf, '(ii)', 'subcontract the Operations.', 10,5) 
         pdf = self.space(pdf)

         pdf = self.column_para_no_seperator(pdf, '(b)', 'If the Operator is a corporation, the Operator is taken to have transferred the licence if:', 10,3)
         pdf = self.column_para_no_seperator(pdf, '(i)', 'anything occurs, the effect of which is to transfer, directly or indirectly, the management or control of the Operator to another person;', 10,3)
         pdf = self.column_para_no_seperator(pdf, '(ii)', 'there is a change of shareholding of the Operator of more than 25 per cent of the issued shares of the Operator.', 10,3)
         pdf = self.space(pdf)

         pdf = self.column_para_no_seperator(pdf, '15.', 'Directions',10,1)
         pdf = self.space(pdf)

         pdf = self.column_para_no_seperator(pdf, '(a)', 'The Operator shall comply with all verbal and written directions issued to it by an inspector appointed pursuant to section 39 of the Act.',10,3)

         pdf = self.space(pdf)
         pdf = self.space(pdf)
         pdf = self.space(pdf)

         pdf = self.create_para(pdf,'Glen McLeod-Thorpe')
         pdf = self.create_para(pdf,app.issue_date.strftime('%d/%m/%Y'))


         #pdf.cell(0, 5, 'Pursuant to Part 4 (Regulation 29) of the Swan and Canning Rivers Management Regulations 2007, this',0,1,'L')
         #pdf.cell(0, 5, 'is to certify that a permit is issued to the person(s) or organisation described hereunder as permit holder',0,1,'L')
         #pdf.cell(0, 5, 'and that person(s) or organisation is permitted to carry out the authorised works, acts or activities for',0,1,'L')
         #pdf.cell(0, 5, 'duration specified, subject to the conditions listed below.',0,1,'L')

#         pdf.cell(0,33,' ', 0,1,'L')
#         pdf.cell(0, 8, 'Swan and Canning Rivers Management Act 2006',0,1,'C')
#         pdf.set_font('Arial', 'B', 10)
#         pdf.cell(0, 8, 'SECTION 84',0,1,'C')
#         pdf.set_font('Arial', 'BU', 10)
#         pdf.cell(0, 8, 'DETERMINATION OF REQUEST FOR VARIATION',0,1,'C')
#         pdf.set_font('Arial', '', 9)   
         BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
         pdf.output(BASE_DIR+'/pdfs/approvals/'+str(app.id)+'-approval.pdf', 'F')


    def generate_section_84(self,app):

         pdf = PDFtool('P', 'mm', 'A4')
         pdf.alias_nb_pages()
         pdf.add_page()
         # pdf.image('plugins/flightsensation/images/flight_voucher.jpg', 0, 0, 210,297)

         #swan_canning_riverpark_dbca.png
         BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
         pdf.image(BASE_DIR+'/applications/static/images/swan_canning_riverpark_dbca.png', 30, 7, 144,24)

         pdf.set_font('Arial', 'I', 10)
         #pdf.cell(0,33,' ', 0,1,'L')
         pdf.cell(0, 8, 'Swan and Canning Rivers Management Act 2006',0,1,'C')
         pdf.set_font('Arial', 'B', 10)
         pdf.cell(0, 8, 'SECTION 84',0,1,'C')
         pdf.set_font('Arial', 'BU', 10)
         pdf.cell(0, 8, 'DETERMINATION OF REQUEST FOR VARIATION',0,1,'C')
         pdf.set_font('Arial', '', 9)

         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         #pdf.cell(6, 5, ' ',0,0,'L')
         #pdf.cell(60, 5, 'FILE NUMBER',0,0,'L')
         #pdf.cell(6, 5, ':',0,0,'L')
         #pdf.cell(6, 5, '1100',0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'APPROVAL NUMBER',0,0,'L')
         pdf.cell(6, 5, ':',0,0,'L')
         pdf.cell(6, 5, '',0,1,'L')
         if app.organisation:
             holder_name = app.organisation.name
         else:
             applicant = SystemUser.objects.get(ledger_id=app.applicant)
             holder_name = applicant.legal_first_name + ' ' + applicant.legal_last_name

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'APPLICANT',0,0,'L')
         pdf.cell(6, 5, ':',0,0,'L')
         pdf.cell(6, 5, holder_name,0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'APPLICANT\'S ADDRESS',0,0,'L')
         pdf.cell(6, 5, ':',0,0,'L')
         pdf.cell(6, 5, '21 cars st kensington',0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'LANDOWNER',0,0,'L')
         pdf.cell(6, 5, ':',0,0,'L')
         pdf.cell(6, 5, '',0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'LAND DESCRIPTION',0,0,'L')
         pdf.cell(6, 5, ':',0,0,'L')
         pdf.cell(6, 5, '',0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'DEVELOPMENT',0,0,'L')
         pdf.cell(6, 5, ':',0,0,'L')
         pdf.cell(6, 5, '',0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'DESCRIPTION OF CHANGES',0,0,'L')
         pdf.cell(6, 5, ':',0,0,'L')
         pdf.cell(6, 5, '',0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'SECTION 84 DETERMINATION',0,0,'L')
         pdf.cell(6, 5, ':',0,0,'L')
         pdf.cell(6, 5, '',0,1,'L')

         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.set_font('Arial', 'B', 10)
         pdf.cell(60, 5, 'DETERMINATION',0,1,'L')
         pdf.set_font('Arial', '', 9)

         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'In accordance with Section 84(1)(a) of the Swan and Canning Rivers Management Act 2006, I hereby:',0,1,'L')

         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(10, 5, '1.',0,0,'L')
         pdf.cell(60, 5, 'Authorise the minor variations to Development Approval [approval number] to allow for [title of section 84].',0,1,'L')

         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(10, 5, '2.',0,0,'L')
         pdf.cell(60, 5, 'Grant this Section 84 approval subject to compliance with all the following conditions and advice notes. All',0,1,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(10, 5, '  ',0,0,'L')
         pdf.cell(60, 5, 'conditions and advice notes shall apply and remain in force for the duration of the approval period.',0,1,'L')

         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.set_font('Arial', 'B', 10)
         pdf.cell(60, 5, 'CONDITIONS',0,1,'L')
         pdf.set_font('Arial', '', 9)

         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(10, 5, '1.',0,0,'L')
         pdf.cell(60, 5, 'Authorise the minor variations to Development Approval [approval number] to allow for [title of section 84].',0,1,'L')

         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(10, 5, '2.',0,0,'L')
         pdf.cell(60, 5, 'Grant this Section 84 approval subject to compliance with all the following conditions and advice notes. All',0,1,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(10, 5, '  ',0,0,'L')
         pdf.cell(60, 5, 'conditions and advice notes shall apply and remain in force for the duration of the approval period.',0,1,'L')



         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.set_font('Arial', 'B', 10)
         pdf.cell(60, 5, 'ADVISE TO APPLICANT',0,1,'L')
         pdf.set_font('Arial', '', 9)

         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(10, 5, '1.',0,0,'L')
         pdf.cell(60, 5, 'Authorise the minor variations to Development Approval [approval number] to allow for [title of section 84].',0,1,'L')

         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(10, 5, '2.',0,0,'L')
         pdf.cell(60, 5, 'Grant this Section 84 approval subject to compliance with all the following conditions and advice notes. All',0,1,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(10, 5, '  ',0,0,'L')
         pdf.cell(60, 5, 'conditions and advice notes shall apply and remain in force for the duration of the approval period.',0,1,'L')

         pdf.cell(0,30,' ', 0,1,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'Stephen Dawson MLC',0,1,'L')
         pdf.set_font('Arial', 'B', 10)
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'MINISTER FOR ENVIRONMENT',0,1,'L')
         pdf.set_font('Arial', '', 9)
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(11, 5, 'DATE:',0,0,'L')
         pdf.cell(60, 5, '20 Feb 2018',0,1,'L')

         pdf.output(BASE_DIR+'/pdfs/approvals/'+str(app.id)+'-approval.pdf', 'F')

    def generate_part5(self,app):

         pdf = PDFtool('P', 'mm', 'A4')
         pdf.alias_nb_pages()
         pdf.add_page()
         # pdf.image('plugins/flightsensation/images/flight_voucher.jpg', 0, 0, 210,297)

         #swan_canning_riverpark_dbca.png
         BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
         pdf.image(BASE_DIR+'/applications/static/images/swan_canning_riverpark_dbca.png', 30, 7, 144,24)

         pdf.set_font('Arial', 'I', 10)
         pdf.cell(0,33,' ', 0,1,'L')
         pdf.cell(0, 8, 'Swan and Canning Rivers Management Act 2006',0,1,'C')
         pdf.set_font('Arial', 'B', 10)
         pdf.cell(0, 8, 'PART 5',0,1,'C')
         pdf.set_font('Arial', 'BU', 10)
         pdf.cell(0, 8, 'DETERMINATION OF DEVELOPMENT APPLICATION',0,1,'C')
         pdf.set_font('Arial', '', 9)

         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         #pdf.cell(6, 5, ' ',0,0,'L')
         #pdf.cell(60, 5, 'FILE NUMBER',0,0,'L')
         #pdf.cell(6, 5, ':',0,0,'L')
         #pdf.cell(6, 5, '1100',0,1,'L')
         if app.organisation:
             holder_name = app.organisation.name
             holder_address = app.organisation.postal_address
         else:
             applicant = SystemUser.objects.get(ledger_id=app.applicant)
             holder_name = applicant.legal_first_name + ' ' + applicant.legal_last_name
             holder_address = SystemUserAddress.objects.get(system_user=applicant, address_type='postal_address')
         landowner = '----'
         land_description = '----'
         if app.application.landowner:
                landowner = app.application.landowner
         if app.application.land_description:
                land_description = app.application.land_description


         pdf = self.column_para_flexi(pdf,'FILE NUMBER','AP-'+str(app.id),None)
         pdf = self.column_para_flexi(pdf,'APPLICANT',holder_name,None)
         pdf = self.column_para_flexi(pdf,'APPLICANT\'S ADDRESS',str(holder_address),None)

         pdf = self.column_para_flexi(pdf,'LANDOWNER',landowner,None)
         pdf = self.column_para_flexi(pdf,'LAND DESCRIPTION',land_description,None)
         pdf = self.column_para_flexi(pdf,'DEVELOPMENT','yes developement allowed',None)

         pdf = self.column_para_flexi(pdf,'VALID FORM 1 RECEIVED','Form 1 received yes',None)
         pdf = self.column_para_flexi(pdf,'DETERMINATION','APPROVAL WITH CONDITIONS',None,'','B')


         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'The application to commence development in accordance with the information received on '+app.application.submit_date.strftime("%d %b %Y")+' is',0,1,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'APPROVED subject to the following conditions:',0,1,'L')
         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         #pdf.cell(6, 5, ' ',0,0,'L')
         #pdf.set_font('Arial', 'B', 10)
         #pdf.cell(60, 5, 'Prior to the commencement of works',0,1,'L')
         #pdf.set_font('Arial', '', 9)
         #pdf.cell(0,2,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(10, 5, '1.',0,0,'L')
         pdf.cell(60, 5, 'Approval to implement this decision is valid for two (2) years from the date of the approval.  If the development',0,1,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(10, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'has not been substantially commenced within this period, a new approval will be required before commencing or',0,1,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(10, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'or completing the development.',0,1,'L')


         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.set_font('Arial', 'B', 9)
         pdf.cell(60, 5, 'CONDITIONS TO APPLICANT',0,1,'L')
         pdf.set_font('Arial', '', 9)

         application_condition = Condition.objects.filter(application=app.application).order_by('condition_no')

         condition_count = 1
         for c in application_condition:
              #condition
              if len(c.condition) > 0 and c.condition_no > 0:
                 pdf = self.column_para_no_seperator(pdf,str(c.condition_no)+'.', c.condition,10,1)
                 pdf = self.space(pdf)
                 condition_count = condition_count + 1


         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.set_font('Arial', 'B', 9)
         pdf.cell(60, 5, 'ADVISE TO APPLICANT',0,1,'L')
         pdf.set_font('Arial', '', 9)

         application_condition = Condition.objects.filter(application=app.application).order_by('advise_no')
         condition_count = 1
         for c in application_condition:
              #advise
              if c.advise_no is None:
                  c.advise_no = 0

              if len(c.advise) > 0 and c.advise_no > 0:
                 pdf = self.column_para_no_seperator(pdf,str(c.advise_no)+'.', c.advise,10,1)
                 pdf = self.space(pdf)
                 condition_count = condition_count + 1


         pdf.cell(0,30,' ', 0,1,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'Stephen Dawson MLC',0,1,'L')
         pdf.set_font('Arial', 'B', 10)
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'MINISTER FOR ENVIRONMENT',0,1,'L')
         pdf.set_font('Arial', '', 9)
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(11, 5, 'DATE:',0,0,'L')      
         pdf.cell(60, 5, '20 Feb 2018',0,1,'L')
         
         pdf.output(BASE_DIR+'/pdfs/approvals/'+str(app.id)+'-approval.pdf', 'F')

    def generate_permitold(self,app):
         BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
         pdf = FPDF('P', 'mm', 'A4')
         pdf.add_page()
         pdf.image(BASE_DIR+'/applications/static/images/parks_and_wildlife_service_dbca.jpg', 30, 7, 144,24)
         pdf.output(BASE_DIR+'/pdfs/approvals/'+str(app.id)+'-permit-approval.pdf', 'F')


    def generate_permit(self,app):
         application_location = Location.objects.filter(application=app.application)
         pdf = PDFtool('P', 'mm', 'A4')
         pdf.alias_nb_pages()
         pdf.add_page()
         # pdf.image('plugins/flightsensation/images/flight_voucher.jpg', 0, 0, 210,297)

         #swan_canning_riverpark_dbca.png
         BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
         pdf.image(BASE_DIR+'/applications/static/images/swan_canning_riverpark_dbca.png', 30, 7, 144,24)

    #     pdf.set_font('Arial', 'I', 10)
   #      pdf.cell(0, 33, ' ',0,0,'L')

#         pdf.cell(6, 5, ' ',0,0,'L')
 #        pdf.cell(0, 5, 'Pursuant to Part 4 (Regulation 29) of the Swan and Canning Rivers Management Regulations 2007, this ',0,1,'L')
  #       pdf.cell(6, 5, ' ',0,0,'L')
 #        pdf.cell(60, 5, 'APPROVED subject to the following conditions:',0,1,'L')
         # group spacer
 #        pdf.cell(0,5,' ', 0,1,'L')


         pdf.set_font('Arial', '', 10)
#         pdf.cell(0,28,' ', 0,1,'L')
         pdf.cell(0, 5, 'Pursuant to Part 4 (Regulation 29) of the Swan and Canning Rivers Management Regulations 2007, this',0,1,'L')
         pdf.cell(0, 5, 'is to certify that a permit is issued to the person(s) or organisation described hereunder as permit holder',0,1,'L')
         pdf.cell(0, 5, 'and that person(s) or organisation is permitted to carry out the authorised works, acts or activities for',0,1,'L')
         pdf.cell(0, 5, 'duration specified, subject to the conditions listed below.',0,1,'L')

         pdf = self.horizontal_line(pdf)

         if app.organisation:
             holder_name = app.organisation.name
         else:
             applicant = SystemUser.objects.get(ledger_id=app.applicant)
             holder_name = applicant.legal_first_name + ' ' + applicant.legal_last_name

         pdf.cell(0,5,' ', 0,1,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'Permit holder',0,0,'L')
         pdf.cell(6, 5, ':',0,0,'L')
         pdf.cell(6, 5, holder_name,0,1,'L')

         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'Authorised works, acts or activities',0,0,'L')
         pdf.cell(6, 5, ':',0,0,'L')
         pdf.cell(6, 5, app.title ,0,1,'L')

         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'Location of works, acts or activities',0,0,'L')
         pdf.cell(6, 5, ':',0,0,'L')

         if application_location.count() > 0:
            pdf.cell(50, 5, application_location[0].lot + ' '+ application_location[0].street_number_name + ' '+application_location[0].suburb,0,0,'L')
         else:
            pdf.cell(50, 5, '' ,0,0,'L')
         pdf.cell(6, 5, '',0,1,'L')

         pdf.cell(0,5,' ', 0,1,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(30, 5, 'Approval date:',0,0,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(50, 5, app.start_date.strftime("%d %b %Y"),0,0,'L')

         pdf.cell(30, 5, 'Expiry date:',0,0,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(30, 5, app.expiry_date.strftime("%d %b %Y"),0,1,'L')

         pdf = self.horizontal_line(pdf)
         # horizontal line
#         pdf.line(7, 110, 205, 110)



         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.set_font('Arial', 'B', 9)
         pdf.cell(60, 5, 'CONDITIONS TO APPLICANT',0,1,'L')
         pdf.set_font('Arial', '', 9)

         application_condition = Condition.objects.filter(application=app.application).order_by('condition_no')

         condition_count = 1
         for c in application_condition:
              #condition
              if len(c.condition) > 0 and c.condition_no > 0:
                 pdf = self.column_para_no_seperator(pdf,str(c.condition_no)+'.', c.condition,10,1)
                 pdf = self.space(pdf)
                 condition_count = condition_count + 1


         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.set_font('Arial', 'B', 9)
         pdf.cell(60, 5, 'ADVISE TO APPLICANT',0,1,'L')
         pdf.set_font('Arial', '', 9)

         application_condition = Condition.objects.filter(application=app.application).order_by('advise_no')

         condition_count = 1
         for c in application_condition:

              if c.advise_no is None:
                   c.advise_no = 0

              #advise
              if len(c.advise) > 0 and c.advise_no > 0:
                  pdf = self.column_para_no_seperator(pdf,str(c.advise_no)+'.', c.advise,10,1)
                  pdf = self.space(pdf)
                  condition_count = condition_count + 1

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.set_font('Arial', 'B', 9)
         pdf.cell(60, 5, 'PERMIT APPROVED',0,1,'L')
         pdf.set_font('Arial', '', 9)

         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(0,15,' ', 0,1,'L')
         pdf.set_font('Arial', '', 10)
         pdf.cell(30, 5, 'Glen Mcleod-Thorpe',0,1,'L')
         pdf.cell(30, 5, app.issue_date.strftime('%d/%m/%Y'),0,1,'L')


#      cell(0, 8, 'Swan and Canning Rivers Management Act 2006',0,1,'C')
#         pdf.set_font('Arial', 'B', 10)
#         pdf.cell(0, 8, 'PART 5',0,1,'C')
#         pdf.set_font('Arial', 'BU', 10)
#         pdf.cell(0, 8, 'DETERMINATION OF DEVELOPMENT APPLICATION',0,1,'C')
#         pdf.set_font('Arial', '', 9)

         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.output(BASE_DIR+'/pdfs/approvals/'+str(app.id)+'-approval.pdf', 'F')

    def generate_emergency_works(self,app):
         application_location = Location.objects.filter(application=app.application)
         pdf = PDFtool('P', 'mm', 'A4')
         pdf.alias_nb_pages()
         pdf.add_page()
         BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
         pdf.image(BASE_DIR+'/applications/static/images/swan_canning_riverpark_dbca.png', 30, 7, 144,24)
         pdf.set_font('Arial', '', 10)

         pdf.cell(0, 5, 'Pursuant to Part 4 (Regulation 29) of the Swan and Canning Rivers Management Regulations 2007, this',0,1,'L')
         pdf.cell(0, 5, 'is to certify that a permit is issued to the person(s) or organisation described hereunder as permit holder',0,1,'L')
         pdf.cell(0, 5, 'and that person(s) or organisation is permitted to carry out the authorised works, acts or activities for',0,1,'L')
         pdf.cell(0, 5, 'duration specified, subject to the conditions listed below.',0,1,'L')

         pdf = self.horizontal_line(pdf)

         if app.organisation:
             holder_name = app.organisation.name
         else:
             applicant = SystemUser.objects.get(ledger_id=app.applicant)
             holder_name = applicant.legal_first_name + ' ' + applicant.legal_last_name

         pdf.cell(0,5,' ', 0,1,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'Permit holder',0,0,'L')
         pdf.cell(6, 5, ':',0,0,'L')
         pdf.cell(6, 5, holder_name,0,1,'L')

         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'Authorised works, acts or activities',0,0,'L')
         pdf.cell(6, 5, ':',0,0,'L')
         pdf.cell(6, 5, "Emergency works: "+app.title ,0,1,'L')

         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(60, 5, 'Location of works, acts or activities',0,0,'L')
         pdf.cell(6, 5, ':',0,0,'L')

         if application_location.count() > 0:
            pdf.cell(50, 5, application_location[0].lot + ' '+ application_location[0].street_number_name + ' '+application_location[0].suburb,0,0,'L')
         else:
            pdf.cell(50, 5, '' ,0,0,'L')
         pdf.cell(6, 5, '',0,1,'L')

         pdf.cell(0,5,' ', 0,1,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(30, 5, 'Approval date:',0,0,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(50, 5, app.start_date.strftime("%d %b %Y"),0,0,'L')

         pdf.cell(30, 5, 'Expiry date:',0,0,'L')
         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.cell(30, 5, app.expiry_date.strftime("%d %b %Y"),0,1,'L')

         pdf = self.horizontal_line(pdf)
         # horizontal line
#         pdf.line(7, 110, 205, 110)



         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.set_font('Arial', 'B', 9)
         pdf.cell(60, 5, 'CONDITIONS TO APPLICANT',0,1,'L')
         pdf.set_font('Arial', '', 9)

         application_condition = Condition.objects.filter(application=app.application).order_by('condition_no')

         condition_count = 1
         for c in application_condition:
              #condition
              if len(c.condition) > 0 and c.condition_no > 0:
                 pdf = self.column_para_no_seperator(pdf,str(c.condition_no)+'.', c.condition,10,1)
                 pdf = self.space(pdf)
                 condition_count = condition_count + 1


         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.cell(6, 5, ' ',0,0,'L')
         pdf.set_font('Arial', 'B', 9)
         pdf.cell(60, 5, 'ADVISE TO APPLICANT',0,1,'L')
         pdf.set_font('Arial', '', 9)

         application_condition = Condition.objects.filter(application=app.application).order_by('advise_no')

         condition_count = 1
         for c in application_condition:

              if c.advise_no is None:
                   c.advise_no = 0

              #advise
              if len(c.advise) > 0 and c.advise_no > 0:
                  pdf = self.column_para_no_seperator(pdf,str(c.advise_no)+'.', c.advise,10,1)
                  pdf = self.space(pdf)
                  condition_count = condition_count + 1


         pdf.cell(0,15,' ', 0,1,'L')
         pdf.set_font('Arial', '', 10)
         pdf.cell(30, 5, 'Glen Mcleod-Thorpe',0,1,'L')
         pdf.cell(30, 5, app.issue_date.strftime('%d/%m/%Y'),0,1,'L')

         # group spacer
         pdf.cell(0,5,' ', 0,1,'L')

         pdf.output(BASE_DIR+'/pdfs/approvals/'+str(app.id)+'-approval.pdf', 'F')

    def get(self,app,self_view,context):
        request = self_view.request
        return context


class MyPDF(FPDF):
    """"""
 
    #----------------------------------------------------------------------
    def header(self):
        """
        Header on each page
        """
        # insert my logo
#        self.image("applications/static/images/parks_and_wildlife_service_dbca.jpg", 10, 8, 23)
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.image(BASE_DIR+'/applications/static/images/swan_canning_riverpark_dbca.png', 30, 7, 144,24)
        # position logo on the right
        self.set_font('Arial', '', 10)
        self.cell(80,5, ' ', 0, 1, 'L')
 
        # set the font for the header, B=Bold
        #self.set_font("Arial", style="B", size=15)
        # page title
        #self.cell(40,10, "Python Rules!", 1, 0, "C")
        # insert a line break of 20 pixels
        self.ln(20)
 
    #----------------------------------------------------------------------
    def footer(self):
        """
        Footer on each page
        """
        # position footer at 15mm from the bottom
        #self.set_y(-15)
 
        # set the font, I=italic
        #self.set_font("Arial", "I", "8")
 
        # display the page number and center it
        #pageNum = "Page %s/{nb}" % self.page_no()
        #self.cell(0, 10, pageNum, align="C")

    def get_li(self): 
 
#----------------------------------------------------------------------
#if __name__ == "__main__":
        pdf = MyPDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_font("Times", '', 12)
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
        # put some lines on the page
        for i in range(1, 50):
            pdf.cell(0, 10, "Line number %s" % i, 0, 1)

        pdf.output(BASE_DIR+"/pdfs/approvals/tutorial3.pdf")
