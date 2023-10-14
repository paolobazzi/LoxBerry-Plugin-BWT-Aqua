#!/usr/bin/perl

# Copyright 2020 Paolo Bazzi, loxberry@bazzi.biz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


##########################################################################
# LoxBerry-Module
##########################################################################
use CGI;
use LoxBerry::System;
use LoxBerry::Web;
use LoxBerry::Log;
  
# Read plugin version
my $version = LoxBerry::System::pluginversion();

# Read POST paramters
my $cgi = CGI->new;
$cgi->import_names('R');

# Create my logging object
my $log = LoxBerry::Log->new ( 
	name => 'HTTP Settup',
	filename => "$lbplogdir/bwt-aqua.log",
	append => 1
	);
LOGSTART "BWT Aqua settings finished.";

# Wir Übergeben die Titelzeile (mit Versionsnummer), einen Link ins Wiki und das Hilfe-Template.
# Um die Sprache der Hilfe brauchen wir uns im Code nicht weiter zu kümmern.
LoxBerry::Web::lbheader("BWT Aqua Plugin V$version", "https://www.loxwiki.eu/display/LOXBERRY/BWT+Aqua", "help.html");
  
# Wir holen uns die Plugin-Config in den Hash %pcfg. Damit kannst du die Parameter mit $pcfg{'Section.Label'} direkt auslesen.
my %pcfg;
tie %pcfg, "Config::Simple", "$lbpconfigdir/pluginconfig.cfg";

# Init template
my $template = HTML::Template->new(
    filename => "$lbptemplatedir/index.html",
    global_vars => 1,
    loop_context_vars => 1,
    die_on_bad_params => 0,
	associate => $cgi,
);

# Init language
my %L = LoxBerry::Web::readlanguage($template, "language.ini");

##########################################################################
# Process form data
##########################################################################
if ($cgi->param("save")) {
	# Data were posted - save 
	&save;
}

my $TYPE = %pcfg{'DEVICE.TYPE'};
my $IP = %pcfg{'DEVICE.IP'};
my $CODE = %pcfg{'DEVICE.CODE'};
my $PRODUCT_CODE = %pcfg{'DEVICE.PRODUCT_CODE'};
my $API_KEY = %pcfg{'DEVICE.API_KEY'};
my $HTTPSEND = %pcfg{'MAIN.HTTP_SEND_ENABLE'};
my $HTTPSENDINTER = %pcfg{'MAIN.HTTP_SEND_INTERVAL'};
my $HTTPPROVIDE = %pcfg{'MAIN.HTTP_PROVIDE'};
my $miniserver = %pcfg{'MAIN.MINISERVER'};


##########################################################################
# Fill Miniserver selection dropdown
##########################################################################
my $MSNO = %pcfg{'MAIN.MINISERVER'};
my $mshtml = LoxBerry::Web::mslist_select_html( FORMID => 'MINISERVER_NO', SELECTED => $miniserver, DATA_MINI => 0, LABEL => "Miniserver" );

$template->param( MINISERVER_HTML => $mshtml);
$template->param( TYPE => $TYPE);
$template->param( IP => $IP);
$template->param( CODE => $CODE);
$template->param( PRODUCT_CODE => $PRODUCT_CODE);
$template->param( API_KEY => $API_KEY);
$template->param( TEST_SITE => "http://$ENV{HTTP_HOST}/plugins/$lbpplugindir/index.cgi?action=test");
$template->param( HTTP_SITE => "http://$ENV{HTTP_HOST}/plugins/$lbpplugindir/index.cgi?action=fetch");
$template->param( LOGDATEI => "/admin/system/tools/logfile.cgi?logfile=plugins/$lbpplugindir/bwt-aqua.log&header=html&format=template");

if ($HTTPSEND == 1) {
	$template->param( HTTPSEND => "checked");
	$template->param( HTTPSENDYES => "selected");
	$template->param( HTTPSENDNO => "");
} else {
	$template->param( HTTPSEND => " ");
	$template->param( HTTPSENDYES => "");
	$template->param( HTTPSENDNO => "selected");
} 
if ($HTTPPROVIDE == 1) {
	$template->param( HTTPPROVIDE => "checked");
	$template->param( HTTPPROVIDEYES => "selected");
	$template->param( HTTPPROVIDENO => "");
} else {
	$template->param( HTTPPROVIDE => " ");
	$template->param( HTTPPROVIDEYES => "");
	$template->param( HTTPPROVIDENO => "selected");
} 

if ($cgi->param("save")) {
	$template->param( SAVED => "1");
}
  
print $template->output();
  
LoxBerry::Web::lbfooter();

LOGEND "BWT Aqua settings finished.";

##########################################################################
# Save data
##########################################################################
sub save 
{

	# We import all variables to the R (=result) namespace
	$cgi->import_names('R');
	
	LOGDEB "Saving settings";

	if ($R::Type eq "") {
		$pcfg{'DEVICE.TYPE'} = "";
		LOGDEB "Type: is empty!";
	} else {
		$pcfg{'DEVICE.TYPE'} = $R::Type;
		LOGDEB "Type: $R::Type";
	}
	
	if ($R::DeviceIp != "") {
		$pcfg{'DEVICE.IP'} = $R::DeviceIp;
		LOGDEB "IP: $R::DeviceIp";
	}
	if ($R::DeviceIp eq "") {
		$pcfg{'DEVICE.IP'} = "";
	}
	
	if ($R::DeviceCode eq "") {
		$pcfg{'DEVICE.CODE'} = "";
	} else {
		$pcfg{'DEVICE.CODE'} = $R::DeviceCode;
		LOGDEB "Code: $R::DeviceCode";
	}

	if ($R::ProductCode eq "") {
		$pcfg{'DEVICE.PRODUCT_CODE'} = "";
	} else {
		$pcfg{'DEVICE.PRODUCT_CODE'} = $R::ProductCode;
		LOGDEB "Product Code: $R::ProductCode";
	}

	if ($R::ApiKey eq "") {
		$pcfg{'DEVICE.API_KEY'} = "";
	} else {
		$pcfg{'DEVICE.API_KEY'} = $R::ApiKey;
		LOGDEB "API Key: $R::ApiKey";
	}
	
	if ($R::MINISERVER_NO != "") {
		$pcfg{'MAIN.MINISERVER'} = $R::MINISERVER_NO;
		LOGDEB "Miniserver: $R::MINISERVER_NO";
	}
	
	if ($R::HTTP_Send == "1") {
		$pcfg{'MAIN.HTTP_SEND_ENABLE'} = "1";
		LOGDEB "HTTP SEND ENABLE 1";
	} else{
		$pcfg{'MAIN.HTTP_SEND_ENABLE'} = "0";
		LOGDEB "HTTP SEND ENABLE 0";
	}
	if ($R::HTTP_Provide == "1") {
		$pcfg{'MAIN.HTTP_PROVIDE_ENABLE'} = "1";
		LOGDEB "HTTP PROVIDE ENABLE 1";
	} else{
		$pcfg{'MAIN.HTTP_PROVIDE_ENABLE'} = "0";
		LOGDEB "HTTP PROVIDE ENABLE 0";
	}
	
	tied(%pcfg)->write();
	LOGDEB "Setting saved";
	return;
}
