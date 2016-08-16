from html import HTML
import xml.etree.ElementTree as ET
import sys
import datetime

result_junit_xml = ET.parse('../ftests/xi_ftest_result_junit.xml')
testsuite = result_junit_xml.getroot()

testcases_by_platform = dict()
testcases_by_name = dict()

''' constructing dictionaries of test cases '''
for testcase in testsuite:
    testcase_name = testcase.attrib['name']
    testcase_name_wo_platform = testcase_name.split(' ')[0]
    testcase_platform = testcase_name.split(' ', 1)[1].split(']')[0].strip()

    testcase_colorcode = 'green'
    for testcase_tag in testcase:
        #print(testcase_tag.tag)

        if (testcase_tag.tag == 'failure' or testcase_tag.tag == 'error'):
            testcase_colorcode = 'red'
        elif (testcase_tag.tag == 'skipped'):
            testcase_colorcode = 'grey' if testcase_tag.attrib['message'] == 'expected test failure' else 'white'

    try:
        testcases_by_name[testcase_name_wo_platform].append([ testcase_platform, testcase_colorcode ])
    except KeyError as ke:
        testcases_by_name[testcase_name_wo_platform] = [ [ testcase_platform, testcase_colorcode ] ]

    try:
        testcases_by_platform[testcase_platform].append([ testcase_name, testcase_colorcode ])
    except KeyError as ke:
        testcases_by_platform[testcase_platform] = [ [ testcase_name, testcase_colorcode ] ]

if (len(testcases_by_platform) == 0):
    sys.exit(0)

xi_test_result_html = HTML("html", "Xively Client Functional Test Result, " +
    "started at " + str(datetime.datetime.now().strftime("%x, %X")))

def fill_in_table(table, testcase_dict, sort_reverse=False):

    keys_sorted = testcase_dict.keys()
    keys_sorted.sort()

    for key in keys_sorted:
        #print(str(key_platform))
        #print(str(testcases_by_platform[key_platform]))
        testcase_dict[key].sort(reverse=sort_reverse)
        row = table.tr
        row.td(key)

        sum_dict = dict()

        for testcase in testcase_dict[key]:
            row.td(bgcolor=testcase[1], title=testcase[0])

            try:
                sum_dict[testcase[1]] += 1
            except KeyError as ke:
                sum_dict[testcase[1]] = 1

        keys_sum = sum_dict.keys()
        #keys_sum.sort()
        for key_sum in keys_sum:
            row.td(str(sum_dict[key_sum]), bgcolor=key_sum)

''' constructing platform table, platforms in rows '''
table_platform = xi_test_result_html.table(border='1', bgcolor='#DDEEDD')

first_row = table_platform.tr
first_row.td('platform', bgcolor='#9acd32')
testcases_by_platform[testcases_by_platform.keys()[0]].sort()
for testcase in testcases_by_platform[testcases_by_platform.keys()[0]]:
    first_row.td(bgcolor='black', title=testcase[0])
''' adding test case counter to the header '''
first_row.td( str( len( testcases_by_platform[testcases_by_platform.keys()[0]] ) ) , bgcolor='lightgrey')

fill_in_table(table_platform, testcases_by_platform)


''' constructing name table, test case names in rows '''
table_name = xi_test_result_html.table(border='1', bgcolor='#DDEEDD')

first_row = table_name.tr
first_row.td('test case', bgcolor='#9acd32')
testcases_by_name[testcases_by_name.keys()[0]].sort(reverse=True)
for testcase in testcases_by_name[testcases_by_name.keys()[0]]:
    first_row.td(testcase[0], bgcolor='#9acd32')

fill_in_table(table_name, testcases_by_name, True)

''' constructing help table '''
table_help = xi_test_result_html.table(border='1')
table_help.tr.td('color codes', bgcolor='lightgreen')
table_help.tr.td('PASS', bgcolor='green')
table_help.tr.td('FAIL', bgcolor='red')
table_help.tr.td('test case is not a requirement', bgcolor='grey')
table_help.tr.td('test case is not implemented', bgcolor='white')


''' printing html to std out '''
print(xi_test_result_html)
