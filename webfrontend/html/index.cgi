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


# Module import
use CGI;
use LoxBerry::System;
use LoxBerry::Web;
use LoxBerry::Log;
use LoxBerry::IO;
use IO::Socket::INET;
use LWP::Simple;
use Net::Ping;
use warnings;
use LWP::UserAgent;
use Data::Dumper;
use HTTP::Request();
use HTTP::Cookies;
use IO::Socket::SSL;
use JSON qw( decode_json );
use POSIX qw( strftime );

print "Content-type: text/html\n\n";

####################################################################################
# (1) Init logfile
###################################################################################
# Create my logging object
my $log = LoxBerry::Log->new ( 
	name => 'HTTP Settup',
	filename => "$lbplogdir/bwt-aqua.log",
	append => 1
	);
LOGSTART "BWT Aqua start";

####################################################################################
# (2a) Init config
###################################################################################
my $pcfgfile = "$lbpconfigdir/pluginconfig.cfg";
my $pcfg;
if (! -e $pcfgfile) {
	$pcfg = new Config::Simple(syntax=>'ini');
	$pcfg->param("MAIN.CONFIG_VERSION", "2");
	$pcfg->write($pcfgfile);
}
$pcfg = new Config::Simple($pcfgfile);

####################################################################################
# (2a) Update old config versions  (v1 -> v2)
###################################################################################
if ($pcfg->param("MAIN.CONFIG_VERSION") eq "1") {
	LOGDEB "Updating plugin config from version 1 to 2";
	print "Updating plugin config from version 1 to 2<br>";
	
	$pcfg->param("MAIN.CONFIG_VERSION", "2");
	# add new parameter values
	$pcfg->param("HTTP_SEND.VIRTUAL_INPUT_COLUMN_1_REMAINING_CAPACITY", "bwt-aqua-column1-remaining-capacity");
	$pcfg->param("HTTP_SEND.VIRTUAL_INPUT_COLUMN_2_REMAINING_CAPACITY", "bwt-aqua-column2-remaining-capacity");
	$pcfg->param("HTTP_SEND.VIRTUAL_INPUT_COLUMN_1_STATE", "bwt-aqua-column1-state");
	$pcfg->param("HTTP_SEND.VIRTUAL_INPUT_COLUMN_2_STATE", "bwt-aqua-column2-state");
	$pcfg->param("HTTP_SEND.VIRTUAL_INPUT_SOLE_COUNTER_LAST_EXTRACTED_QUANTITY", "bwt-aqua-sole-counter-last-extracted-quantity");
	$pcfg->write($pcfgfile);
}

####################################################################################
# (2c) Read config
###################################################################################

$HTTP_SEND_ENABLE = $pcfg->param("MAIN.HTTP_SEND_ENABLE");
$HTTP_SEND_INTERVAL = $pcfg->param("MAIN.HTTP_SEND_INTERVAL");
$BWT_IP = $pcfg->param("DEVICE.IP");
$BWT_CODE = $pcfg->param("DEVICE.CODE");
$MINISERVER = $pcfg->param('MAIN.MINISERVER');

# Check mode
my $cgi = CGI->new;
$cgi->import_names('R');
$TEST_MODE = $R::action eq "test";			# TEST Mode: Read values from BWT regenrant and print as HTML output including verbose logging (and send values to MiniServer if enabled)
$FETCH_MODE = $R::action eq "fetch";		# FETCH Mode: Read values from BWT regenerant and print as formatted HTML output (do not send values to MiniServer)
$TRIGGER_MODE = $R::action eq "trigger";	# TRIGGER Mode: Send action (ID & value) to BWT regenrant
											# Parameterless Mode: Read values froM BWT regenerant (and send values to MiniServer if enabled)

LOGDEB "BWT IP: ".$BWT_IP;
LOGDEB "BWT CODE: ".$BWT_CODE;
LOGDEB "HTTP SEND ENABLE: ".$HTTP_SEND_ENABLE;
LOGDEB "HTTP SEND INTERVAL: ".$HTTP_SEND_INTERVAL;
LOGDEB "MINISERVER NO: ".$MINISERVER;

if ($TEST_MODE) {
	print "Configuration:<br>";
	print "- BWT IP: ".$BWT_IP."<br>";
	print "- BWT CODE: ".$BWT_CODE."<br>";
	print "- HTTP SEND ENABLE: ".$HTTP_SEND_ENABLE."<br>";
	print "- HTTP SEND INTERVAL: ".$HTTP_SEND_INTERVAL."<br>";
	print "- MINISERVER NO: ".$MINISERVER."<br>";
	print "<hr>";
}

####################################################################################
# (3) Check for valid mode
####################################################################################

if (!$TEST_MODE && !$FETCH_MODE && !$TRIGGER_MODE && !$HTTP_SEND_ENABLE) {
	LOGDEB "Not testing and not fetch and not trigger mode and not HTTP send enable. Abort processing.";
	exit 0;
}

####################################################################################
# (4) Login to BWT regenrant
####################################################################################
my $url = 'http://'.$BWT_IP.'/users/login';
my $header = ['Content-Type' => 'application/x-www-form-urlencoded'];
my $req = HTTP::Request->new('POST', $url, $header, '_method=POST&STLoginPWField='.$BWT_CODE.'&function=save' );
my $cookie_jar = HTTP::Cookies->new;
my $ua = LWP::UserAgent->new();
push @{ $ua->requests_redirectable }, 'POST';
$ua->ssl_opts(
    SSL_verify_mode => IO::Socket::SSL::SSL_VERIFY_NONE, 
    verify_hostname => 0
);
$ua->cookie_jar($cookie_jar);

if ($TEST_MODE) {
	print "Login to BWT Aqua<br>";
}

my $response = $ua->request($req);

if ($response->code == 200) {
	LOGDEB "Login OK";
	if ($TEST_MODE) {
		printf "Login OK"."<br>";
	}
} else {
	LOGDEB "Login failed. Error Code: ".$response->code.", Message: ".$response->message;
	if ($TEST_MODE) {
		printf "Login failed. Error Code: ".$response->code.", Message: ".$response->message."<br>";
		$Data::Dumper::Pad = '<br>';
		printf "<p style='color:red;'>";
		printf Dumper $response;
		printf "</p>";
	}
	exit 0;
}

if ($TRIGGER_MODE) {
	####################################################################################
	# (5a) Trigger action in BWT
	####################################################################################
	$ID = $R::id;			# BWT Action ID
	$VALUE = $R::value; 	# BWT Action value
	
	my $url = 'http://'.$BWT_IP.'/keyboard/saveValue';
	my $header = ['Content-Type' => 'application/x-www-form-urlencoded'];
	my $req = HTTP::Request->new('POST', $url, $header, 'ID='.$ID.'&Value='.$VALUE);
	$ua = LWP::UserAgent->new();
	push @{ $ua->requests_redirectable }, 'POST';
	$ua->ssl_opts(
	    SSL_verify_mode => IO::Socket::SSL::SSL_VERIFY_NONE, 
	    verify_hostname => 0
	);
	$ua->cookie_jar($cookie_jar);
	$response = $ua->request($req);
	if ($response->code == 200) {
		LOGDEB "Trigger action id=".$ID.", value=".$VALUE." successful, message: ".$response->message;
		print "Trigger action id=".$ID.", value=".$VALUE." successful, message: ".$response->message."<br>";
	} else {
		LOGDEB "Trigger action id=".$ID.", value=".$VALUE." failed. Error Code: ".$response->code.", Message: ".$response->message;
		print "Trigger action id=".$ID.", value=".$VALUE." failed. Error Code: ".$response->code.", Message: ".$response->message."<br>";
	}
	exit 0;	
} else {
	####################################################################################
	# (5b) Read data from BWT
	####################################################################################

	# Request 1: /home/actualizedata
	$url = 'https://'.$BWT_IP.'/home/actualizedata';
	$req = HTTP::Request->new('GET', $url);
	$ua = LWP::UserAgent->new();
	$ua->ssl_opts(
	    SSL_verify_mode => IO::Socket::SSL::SSL_VERIFY_NONE, 
	    verify_hostname => 0
	);
	$ua->cookie_jar($cookie_jar);
	
	if ($TEST_MODE) {
		print "Reading data from BWT Aqua regenerant<br>";
	}
	
	$response = $ua->request($req);
	if ($response->code == 200) {
		LOGDEB "Read data OK";
		if ($TEST_MODE) {
			printf "Read data OK"."<br>";
		}
	} else {
		LOGDEB "Read data failed. Error Code: ".$response->code.", Message: ".$response->message;
		if ($TEST_MODE) {
			printf "Read data failed. Error Code: ".$response->code.", Message: ".$response->message."<br>";
			$Data::Dumper::Pad = '<br>';
			printf "<p style='color:red;'>";
			printf Dumper $response;
			printf "</p>";
		}
		exit 0;
	}
	
	# Request 2: /info/updateDetails2
	$url2 = 'https://'.$BWT_IP.'/info/updateDetails2';
	$req2 = HTTP::Request->new('GET', $url2);
	$response2 = $ua->request($req2);
	if ($response2->code == 200) {
		LOGDEB "Read detail data OK";
		if ($TEST_MODE) {
			printf "Read detail data OK"."<br>";
		}
	} else {
		LOGDEB "Read detail data failed. Error Code: ".$response2->code.", Message: ".$response2->message;
		if ($TEST_MODE) {
			printf "Read detail data failed. Error Code: ".$response2->code.", Message: ".$response2->message."<br>";
			$Data::Dumper::Pad = '<br>';
			printf "<p style='color:red;'>";
			printf Dumper $response2;
			printf "</p>";
		}
		## exit 0;
	}
	
	## TODO gather further informations 
	## https://192.168.1.54/functions/holidaymode   get status
	## https://192.168.1.54/info/getblendblock
	
	if ($TEST_MODE) {
		print "<hr>";
	}
	
	my $decoded_json = decode_json( $response->content );
	my $decoded_json2 = decode_json( $response2->content );
	my $timestampString = strftime("%d.%m.%Y %H:%M:%S", localtime(time));
	my $timestamp = epoch2lox();	
 
	if ($TEST_MODE) {
		print "Raw values:"."<br>";
	}
	## actualizeData values
	print "flowCurrent=".$decoded_json->{aktuellerDurchfluss}."<br>";
	print "flowCurrentPercent=".$decoded_json->{aktuellerDurchflussProzent}."<br>";
	print "flowToday=".$decoded_json->{durchflussHeute}."<br>";
	print "flowMonth=".$decoded_json->{durchflussMonat}."<br>";
	print "flowYear=".($decoded_json->{durchflussJahr} / 10)."<br>";
	print "regenerantRefillDays=".$decoded_json->{RegeneriemittelNachfuellenIn}."<br>";
	print "regenerantRemainingDays=".$decoded_json->{RegeneriemittelVerbleibend}."<br>";

	## updateDetails values	
	#print "durchfluss=".$decoded_json2->{durchfluss}." <i>Liter/h</i><br>";
	print "remainingCapacityColumn1=".$decoded_json2->{restkap1}."<br>";
	print "remainingCapacityColumn2=".$decoded_json2->{restkap2}."<br>";
	print "stateColumn1=".$decoded_json2->{step1}."<br>";
	print "stateColumn2=".$decoded_json2->{step2}."<br>";
	#print "restlz1=".$decoded_json2->{restlz1}."<br>";
	#print "restlz1=".$decoded_json2->{restlz2}."<br>";
	#print "saugrate=".$decoded_json2->{saugrate}."<br>";
	print "soleCounterLastExtractedQuantity=".$decoded_json2->{menge}."<br>";

	## timestamp(s)		
	#print "timestamp=".$timestamp." <i>(Sekunden seit 1.1.2009 - Loxone Epoch Time)</i><br>";
	print "timestamp=".$timestamp."<br>";
	print "timestampString=".$timestampString;
	
	if ($TEST_MODE) {
		print "<hr>";
	}
	
	####################################################################################
	# Send values to Miniserver
	###################################################################################
	if ($HTTP_SEND_ENABLE && !$FETCH_MODE && !$TRIGGER_MODE) {
		LOGDEB "Start sending values to Miniserver";
		if ($TEST_MODE) {
			print "Start sending values to Miniserver<br>";
		}
		
		$VI_FLOW_CURRENT 							= $pcfg->param("HTTP_SEND.VIRTUAL_INPUT_FLOW_CURRENT");
		$VI_FLOW_CURRENT_PERCENT 					= $pcfg->param("HTTP_SEND.VIRTUAL_INPUT_FLOW_CURRENT_PERCENT");
		$VI_FLOW_TODAY			 					= $pcfg->param("HTTP_SEND.VIRTUAL_INPUT_FLOW_TODAY");
		$VI_FLOW_MONTH			 					= $pcfg->param("HTTP_SEND.VIRTUAL_INPUT_FLOW_MONTH");
		$VI_FLOW_YEAR			 					= $pcfg->param("HTTP_SEND.VIRTUAL_INPUT_FLOW_YEAR");
		$VI_REGENERANT_REFILL_DAYS 					= $pcfg->param("HTTP_SEND.VIRTUAL_INPUT_REGENERANT_REFILL_DAYS");
		$VI_REGENERANT_REFILL_REMAINING 			= $pcfg->param("HTTP_SEND.VIRTUAL_INPUT_REGENERANT_REMAINING");
		$VI_DATA_TIMESTAMP							= $pcfg->param("HTTP_SEND.VIRTUAL_INPUT_DATA_TIMESTAMP");
		$VI_COLUMN_1_REMAINING_CAPACITY 			= $pcfg->param("HTTP_SEND.VIRTUAL_INPUT_COLUMN_1_REMAINING_CAPACITY");
		$VI_COLUMN_2_REMAINING_CAPACITY 			= $pcfg->param("HTTP_SEND.VIRTUAL_INPUT_COLUMN_2_REMAINING_CAPACITY");
		$VI_COLUMN_1_STATE							= $pcfg->param("HTTP_SEND.VIRTUAL_INPUT_COLUMN_1_STATE");
		$VI_COLUMN_2_STATE 							= $pcfg->param("HTTP_SEND.VIRTUAL_INPUT_COLUMN_2_STATE");
		$VI_SOLE_COUNTER_LAST_EXTRACTED_QUANTITY	= $pcfg->param("HTTP_SEND.VIRTUAL_INPUT_SOLE_COUNTER_LAST_EXTRACTED_QUANTITY");
		
		# Set this variable directly before the function call to override the cache and exceptionally submit ALL values.
		# After every function call, the function resets the value to 0.
		### $LoxBerry::IO::mem_sendall = 1;
		
		my %data_to_send;
		$data_to_send{$VI_FLOW_CURRENT} 						= $decoded_json->{aktuellerDurchfluss};
		$data_to_send{$VI_FLOW_CURRENT_PERCENT} 				= $decoded_json->{aktuellerDurchflussProzent};
		$data_to_send{$VI_FLOW_TODAY} 							= $decoded_json->{durchflussHeute};
		$data_to_send{$VI_FLOW_MONTH} 							= $decoded_json->{durchflussMonat};
		$data_to_send{$VI_FLOW_YEAR} 							= ($decoded_json->{durchflussJahr} / 10);
		$data_to_send{$VI_REGENERANT_REFILL_DAYS} 				= $decoded_json->{RegeneriemittelNachfuellenIn};
		$data_to_send{$VI_REGENERANT_REFILL_REMAINING} 			= $decoded_json->{RegeneriemittelVerbleibend};
		
		$data_to_send{$VI_COLUMN_1_REMAINING_CAPACITY} 			= $decoded_json2->{restkap1};
		$data_to_send{$VI_COLUMN_2_REMAINING_CAPACITY} 			= $decoded_json2->{restkap2};
		$data_to_send{$VI_COLUMN_1_STATE} 						= $decoded_json2->{step1};
		$data_to_send{$VI_COLUMN_2_STATE} 						= $decoded_json2->{step2};
		$data_to_send{$VI_SOLE_COUNTER_LAST_EXTRACTED_QUANTITY} = $decoded_json2->{menge};
	
		$data_to_send{$VI_DATA_TIMESTAMP}	 					= $timestampString;
		
		my %response = LoxBerry::IO::mshttp_send($MINISERVER, %data_to_send);
		if (! $response{$VI_FLOW_CURRENT}) {
		    print STDERR "Error sending ".$VI_FLOW_CURRENT."<br>";
		    LOGWARN "Error sending ".$VI_FLOW_CURRENT;
		}
		if (! $response{$VI_FLOW_CURRENT_PERCENT}) {
		    print STDERR "Error sending ".$VI_FLOW_CURRENT_PERCENT."<br>";
			LOGWARN	"Error sending ".$VI_FLOW_CURRENT_PERCENT;
		}
		if (! $response{$VI_FLOW_TODAY}) {
		    print STDERR "Error sending ".$VI_FLOW_TODAY."<br";
		    LOGWARN "Error sending ".$VI_FLOW_TODAY;
		}
		if (! $response{$VI_FLOW_MONTH}) {
		    print STDERR "Error sending ".$VI_FLOW_MONTH."<br>";
		    LOGWARN "Error sending ".$VI_FLOW_MONTH;
		}
		if (! $response{$VI_FLOW_YEAR}) {
		    print STDERR "Error sending ".$VI_FLOW_YEAR."<br>";
		    LOGWARN "Error sending ".$VI_FLOW_YEAR;
		}
		if (! $response{$VI_REGENERANT_REFILL_DAYS}) {
		    print STDERR "Error sending ".$VI_REGENERANT_REFILL_DAYS."<br>";
		    LOGWARN "Error sending ".$VI_REGENERANT_REFILL_DAYS;
		}
		if (! $response{$VI_REGENERANT_REFILL_REMAINING}) {
		    print STDERR "Error sending ".$VI_REGENERANT_REFILL_REMAINING."<br>";
		    LOGWARN "Error sending ".$VI_REGENERANT_REFILL_REMAINING;
		}
		if (! $response{$VI_COLUMN_1_REMAINING_CAPACITY}) {
		    print STDERR "Error sending ".$VI_COLUMN_1_REMAINING_CAPACITY."<br>";
		    LOGWARN "Error sending ".$VI_COLUMN_1_REMAINING_CAPACITY;
		}
		if (! $response{$VI_COLUMN_2_REMAINING_CAPACITY}) {
		    print STDERR "Error sending ".$VI_COLUMN_2_REMAINING_CAPACITY."<br>";
		    LOGWARN "Error sending ".$VI_COLUMN_2_REMAINING_CAPACITY;
		}
		if (! $response{$VI_COLUMN_1_STATE}) {
		    print STDERR "Error sending ".$VI_COLUMN_1_STATE."<br>";
		    LOGWARN "Error sending ".$VI_COLUMN_1_STATE;
		}
		if (! $response{$VI_COLUMN_2_STATE}) {
		    print STDERR "Error sending ".$VI_COLUMN_2_STATE."<br>";
		    LOGWARN "Error sending ".$VI_COLUMN_2_STATE;
		}
		if (! $response{$VI_SOLE_COUNTER_LAST_EXTRACTED_QUANTITY}) {
		    print STDERR "Error sending ".$VI_SOLE_COUNTER_LAST_EXTRACTED_QUANTITY."<br>";
		    LOGWARN "Error sending ".$VI_SOLE_COUNTER_LAST_EXTRACTED_QUANTITY;
		}
		if (! $response{$VI_DATA_TIMESTAMP}) {
		    print STDERR "Error sending ".$VI_DATA_TIMESTAMP."<br>";
		    LOGWARN "Error sending ".$VI_DATA_TIMESTAMP;
		}
		
		LOGDEB "Finished sending values to Miniserver";
		
		if ($TEST_MODE) {
			while ( ($k,$v) = each %data_to_send ) {
	    		print "- $k => $v\n"."<br>";
			}	
			print "Finished sending values to Miniserver<br>";
		}
	} else {
		LOGDEB "Sending values to Miniserver using HTTP is disabled or using fetch/trigger mode.";
		if ($TEST_MODE) {
			print "Sending values to Miniserver using HTTP is disabled.<br>";
		}
	}
}
LOGEND "Operation finished sucessfully.";

