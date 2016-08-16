<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<xsl:key name="platform" match="testsuite/testcase/@name" use="substring-after(., ' ')"/>
<xsl:key name="testcase" match="testsuite/testcase/@name" use="substring-before(., ' ')"/>

<xsl:template name="printcell">
    <xsl:choose>
        <xsl:when test="failure">
            <td bgcolor="red" title="{substring-before(@name, ' ')}"/>
        </xsl:when>
        <xsl:when test="error">
        </xsl:when>
        <xsl:when test="skipped">
            <xsl:choose>
                <xsl:when test="skipped/@message = 'expected test failure'">
                    <td bgcolor="grey" title="{substring-before(@name, ' ')}"/>
                </xsl:when>
                <xsl:otherwise>
                    <td bgcolor="white" title="{substring-before(@name, ' ')}"/>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:when>
        <xsl:otherwise>
            <td bgcolor="green" title="{substring-before(@name, ' ')}"/>
        </xsl:otherwise>
    </xsl:choose>
</xsl:template>

<xsl:template match="/">
    <html>
    <body>
    <h2>Xively Client Functional Test Result Sheet</h2>

    <!-- digest table -->
    <table border="1" bgcolor="#DDEEDD">
        <tr bgcolor="#9acd32">

            <th>platform</th>

            <xsl:for-each select="testsuite/testcase/@name[generate-id() = generate-id(key('testcase', substring-before(., ' ')))]">
                <th bgcolor="black" title="{substring-before(., ' ')}"></th>
                <xsl:choose>
                    <xsl:when test="position() = last()">
                        <th><xsl:value-of select="position()"/></th>
                        <!--th>
                            <xsl:value-of select="count(../../testcase[(generate-id(@name) = generate-id(key('testcase', substring-before(@name, ' '))))])"/>
                        </th-->
                    </xsl:when>
                </xsl:choose>
            </xsl:for-each>

            <xsl:for-each select="testsuite/testcase">
                <xsl:sort select="substring-after(@name, ' ')"/>

                <xsl:choose>
                    <xsl:when test="(generate-id(@name) = generate-id(key('platform', substring-after(@name, ' '))))">

                        <tr></tr>
                        <td><xsl:value-of select="substring-before(substring-after(@name, ' '), ' ')"/></td>

                        <xsl:call-template name="printcell"/>

                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:call-template name="printcell"/>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:for-each>
        </tr>
    </table>

    <!-- extended table -->
    <table border="1" bgcolor="#DDEEDD">
        <tr bgcolor="#9acd32">
            <th>test case</th>
            <xsl:for-each select="testsuite/testcase/@name[generate-id() = generate-id(key('platform', substring-after(., ' ')))]">
                <th>
                    <xsl:value-of select="substring-before(substring-after(., ' '), ' ')"/>
                </th>
            </xsl:for-each>

            <xsl:for-each select="testsuite/testcase">
                <xsl:sort select="substring-before(@name, ' ')"/>
                <xsl:choose>
                    <xsl:when test="(generate-id(@name) = generate-id(key('testcase', substring-before(@name, ' '))))">
                        <tr></tr>
                        <td><xsl:value-of select="substring-before(@name, ' ')"/></td>

                        <xsl:call-template name="printcell"/>

                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:call-template name="printcell"/>

                    </xsl:otherwise>
                </xsl:choose>
            </xsl:for-each>
        </tr>
    </table>

    <!-- color codes -->
    <table border="1">
        <tr><td>color codes</td></tr>
        <tr><td bgcolor="green">PASS</td></tr>
        <tr><td bgcolor="red">FAIL</td></tr>
        <tr><td bgcolor="grey">test case is not a requirement</td></tr>
        <tr><td bgcolor="white">test case is not implemented</td></tr>
    </table>

  </body>
  </html>
</xsl:template>

</xsl:stylesheet>
