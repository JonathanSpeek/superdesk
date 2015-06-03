# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import xml.etree.ElementTree as etree
from xml.etree.ElementTree import SubElement
from apps.publish.formatters import Formatter
import superdesk
from superdesk.errors import FormatterError
from superdesk.utc import utcnow


class NewsML12Formatter(Formatter):
    """
    NewsML 1.2 Formatter
    """
    XML_ROOT = '<?xml version="1.0"?><!DOCTYPE NewsML SYSTEM "http://www.aap.com.au/xml-res/NewsML_1.2.dtd">'
    USAGE_TYPE = 'AAP content is owned by or licensed to Australian Associated Press Pty Limited (AAP) and is ' \
                 'copyright protected.  AAP content is published on an "as is" basis for personal use only and ' \
                 'must not be copied, republished, rewritten, resold or redistributed, whether by caching, ' \
                 'framing or similar means, without AAP\'s prior written permission.  AAP and its licensors ' \
                 'are not liable for any loss, through negligence or otherwise, resulting from errors or ' \
                 'omissions in or reliance on AAP content.  The globe symbol and "AAP" are registered trade marks. ' \
                 'Further this AAP content is supplied to the direct recipient pursuant to an Information Supply ' \
                 'Agreement with AAP (AAP Information Supply Agreement).  The direct recipient has a non-exclusive, ' \
                 'non-transferable right to display this AAP content in accordance with and subject to the ' \
                 'terms of the AAP Information Supply Agreement.'
    LIMITATIONS = 'The direct recipient must comply with the limitations specified in the AAP Information ' \
                  'Supply Agreement relating to the AAP content including, without limitation, not permitting ' \
                  'redistribution and storage of the content (outside the terms of the Agreement) and not ' \
                  'permitting deep hyperlinking to the content, framing of the content on a web site, ' \
                  'posting the content to usenet newsgroups or facilitating such actions.'
    now = utcnow()

    def format(self, article, destination, selector_codes=None):
        try:

            pub_seq_num = superdesk.get_resource_service('output_channels').generate_sequence_number(destination)

            newsml = etree.Element("NewsML")
            SubElement(newsml, "Catalog", {'Href': 'http://www.aap.com.au/xml-res/aap-master-catalog.xml'})
            news_envelope = SubElement(newsml, "NewsEnvelope")
            news_item = SubElement(newsml, "NewsItem")

            self.__format_news_envelope(article, news_envelope, pub_seq_num)
            self.__format_identification(article, news_item)
            self.__format_news_management(article, news_item)
            self.__format_news_component(article, news_item)

            return pub_seq_num, self.XML_ROOT + str(etree.tostring(newsml))
        except Exception as ex:
            raise FormatterError.newml12FormatterError(ex, destination)

    def __format_news_envelope(self, article, news_envelope, pub_seq_num):
        SubElement(news_envelope, 'TransmissionId').text = pub_seq_num
        SubElement(news_envelope, 'DateAndTime').text = self.now.strftime('%Y%m%dT%H%M%S+0000')
        SubElement(news_envelope, 'Priority', {'FormalName': article.get('priority', '')})

    def __format_identification(self, article, news_item):
        revision = self.__process_revision(article)
        identification = SubElement(news_item, "Identification")
        news_identifier = SubElement(identification, "NewsIdentifier")
        SubElement(news_identifier, 'ProviderId').text = 'aap.com.au'
        SubElement(news_identifier, 'DateId').text = self.now.strftime("%Y%m%d")
        SubElement(news_identifier, 'NewsItemId').text = article['_id']
        SubElement(news_identifier, 'RevisionId', revision).text = str(article.get('_version', ''))
        SubElement(news_identifier, 'PublicIdentifier').text = article['_id']
        SubElement(identification, "DateLabel").text = self.now.strftime("%A %d %B %Y")

    def __process_revision(self, article):
        # Implementing the corrections
        # For the re-writes 'RelatesTo' field will be user
        revision = {'PreviousRevision': '0', 'Update': 'N'}
        if article['state'] == 'corrected':
            revision['PreviousRevision'] = str(article.get('_version') - 1)
            revision['Update'] = 'A'
        return revision

    def __format_news_management(self, article, news_item):
        news_management = SubElement(news_item, "NewsManagement")
        SubElement(news_management, 'NewsItemType', {'FormalName': 'News'})
        SubElement(news_management, 'FirstCreated').text = article['firstcreated']
        SubElement(news_management, 'ThisRevisionCreated').text = article['versioncreated']
        SubElement(news_management, 'Status', {'FormalName': article['pubstatus']})
        SubElement(news_management, 'Urgency', {'FormalName': article['urgency']})
        if article['state'] == 'corrected':
            SubElement(news_management, 'Instruction', {'FormalName': 'Correction'})
        else:
            SubElement(news_management, 'Instruction', {'FormalName': 'Update'})

    def __format_news_component(self, article, news_item):
        news_component = SubElement(news_item, "NewsComponent")
        main_news_component = SubElement(news_component, "NewsComponent")
        SubElement(main_news_component, 'Role', {'FormalName': 'Main'})
        self.__format_news_lines(article, main_news_component)
        self.__format_rights_metadata(article, main_news_component)
        self.__format_descriptive_metadata(article, main_news_component)
        self.__format_abstract(article, main_news_component)
        self.__format_body(article, main_news_component)

    def __format_news_lines(self, article, main_news_component):
        news_lines = SubElement(main_news_component, "NewsLines")
        SubElement(news_lines, 'Headline').text = article.get('headline', '')
        SubElement(news_lines, 'ByLine').text = article.get('byline', '')
        SubElement(news_lines, 'DateLine').text = article.get('dateline', '')
        SubElement(news_lines, 'CreditLine').text = article.get('creditline', '')
        SubElement(news_lines, 'KeywordLine').text = article.get('keywords')[0]

    def __format_rights_metadata(self, article, main_news_component):
        rights_metadata = SubElement(main_news_component, "RightsMetadata")
        copyright = SubElement(rights_metadata, "Copyright")
        SubElement(copyright, 'CopyrightHolder').text = article.get('source', article.get('original_source', ''))
        SubElement(copyright, 'CopyrightDate').text = self.now.strftime("%Y")

        usage_rights = SubElement(rights_metadata, "UsageRights")
        SubElement(usage_rights, 'UsageType').text = self.USAGE_TYPE
        SubElement(usage_rights, 'Geography').text = article.get('place', article.get('located', ''))
        SubElement(usage_rights, 'RightsHolder').text = article.get('source', article.get('original_source', ''))
        SubElement(usage_rights, 'Limitations').text = self.LIMITATIONS
        SubElement(usage_rights, 'StartDate').text = self.now
        SubElement(usage_rights, 'EndDate').text = self.now

    def __format_descriptive_metadata(self, article, main_news_component):
        descriptive_metadata = SubElement(main_news_component, "DescriptiveMetadata")
        subject_code = SubElement(descriptive_metadata, "SubjectCode")

        for subject in article.get('subject', []):
            SubElement(subject_code, 'Subject', {'FormalName': subject.get('qcode', '')})

        # For now there's only one category
        SubElement(descriptive_metadata, 'Property',
                   {'FormalName': 'Category', 'Value': article['anpa-category']['qcode']})

        # TODO: Subcategory
        # TODO: Locator

    def __format_abstract(self, article, main_news_component):
        abstract_news_component = SubElement(main_news_component, "NewsComponent")
        SubElement(abstract_news_component, 'Role', {'FormalName': 'Abstract'})
        content_item = SubElement(abstract_news_component, "ContentItem")
        SubElement(content_item, 'MediaType', {'FormalName': 'Text'})
        SubElement(content_item, 'Format', {'FormalName': 'Text'})
        SubElement(content_item, 'DataContent').text = article.get('abstract', '')

    def __format_body(self, article, main_news_component):
        body_news_component = SubElement(main_news_component, "NewsComponent")
        SubElement(body_news_component, 'Role', {'FormalName': 'BodyText'})
        SubElement(body_news_component, 'Format', {'FormalName': 'Text'})
        content_item = SubElement(body_news_component, "ContentItem")
        SubElement(content_item, 'MediaType', {'FormalName': 'Text'})
        SubElement(content_item, 'Format', {'FormalName': 'Text'})
        SubElement(content_item, 'DataContent').text = article.get('body_html', '')

    def can_format(self, format_type, article_type):
        return format_type == 'newsml12' and article_type in ['text', 'preformatted', 'composite']
