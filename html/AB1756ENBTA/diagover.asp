<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">

<html>
<head>
	<title>Rockwell Automation</title>
	<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
	<link type="text/css" href="css/radevice.css" rel="stylesheet">
	<script type="text/javascript" language="JavaScript" src="scripts/URLhandle.js"></script>
	<script language="javascript" type="text/javascript" src="scripts/refresh.js"></script>
</head>

<body onLoad="frame_check(); refreshInit();" bgcolor="#B7B6B6" leftmargin="0" topmargin="0" rightmargin="0" bottommargin="0" marginwidth="0">
<div style="margin-left: 10px;">
<!-- Start tabs -->
<table width="98%" border="0" cellspacing="0" cellpadding="0">
	<tr>
		<td nowrap width="6" valign="top"><img src="images/menustarton.gif" alt="" width="10" 
	  height="16" border="0" /></td>
		<td nowrap background="images/menubgon.gif">Diagnostic Overview</td>
		<td nowrap><img src="images/menseponoff.gif" width="23" height="16" border="0"></td>
		<td nowrap background="images/menubgoff.gif">
			<a class="tab" onClick="highlightTree('/diagnetwork.asp');" href="diagnetwork.asp">Network Settings</a></td>
		<td nowrap><img src="images/mensepoffoff.gif" width="23" height="16" border="0"></td>
		<td nowrap background="images/menubgoff.gif">
			<a class="tab" onClick="highlightTree('/msgconnect.asp');" href="msgconnect.asp">Message Connections</a></td>
		<td nowrap><img src="images/mensepoffoff.gif" width="23" height="16" border="0"></td>
		<td nowrap background="images/menubgoff.gif">
			<a class="tab" onClick="highlightTree('/ioconnect.asp');" href="ioconnect.asp">I/O Connections</a></td>
		<td nowrap><img src="images/mensepoffoff.gif" width="23" height="16" border="0"></td>
		<td nowrap background="images/menubgoff.gif">
			<a class="tab" onClick="highlightTree('/etherstats.asp');" href="etherstats.asp">Ethernet Statistics</a></td>
		<td nowrap><img src="images/menuendoff.gif" width="21" height="16" border="0"></td>
		<td nowrap width="100%" align="right" background="images/menuendbg.gif"></td>
	</tr>
</table>
<!-- End tabs -->
<!-- Start tab background -->
<table width="98%" border="0" cellspacing="0" cellpadding="0" bgcolor="#002569">
	<tr>
		<td width="1"><img src="images/border.gif" width="1" height="1" border="0"></td>
		<td width="100%" bgcolor="#FFFFFF">
		<br>
		<!-- Body starts here -->
		<table width="100%" border="0" cellspacing="10" cellpadding="0">
			<tr>
				<td valign="top" class="subhead">
				
						<table border="0" cellspacing="0" cellpadding="4">
							<tr class="tablehead">
								<td colspan="2" bgcolor="#BDC8DD">Ethernet Link</td>
							</tr>
							<tr class="row">
								<td width="250">Speed</td>
								<td width="150">100 Mbps</td>
							</tr>
							<tr bgcolor="#dedede">
								<td width="250">Duplex</td>
								<td width="150">Full Duplex</td>
							</tr>
							<tr class="row">
								<td width="250">Autonegotiate Status</td>
								<td width="150">Autonegotiate Speed and Duplex</td>
							</tr>
						</table>
						<br>
						<table border="0" cellspacing="0" cellpadding="4">
							<tr class="tablehead">
								<td colspan="2" bgcolor="#BDC8DD">System Resource Utilization</td>
							</tr>
							<tr class="row">
								<td width="250">CPU</td>
								<td width="150">14.90 %</td>
							</tr>
						</table>
						<br>
						<table border="0" cellspacing="0" cellpadding="4">
							<tr class="tablehead">
								<td colspan="2" bgcolor="#BDC8DD">Web Server</td>
							</tr>
							<tr class="row">
								<td width="250">Server Errors</td>
								<td width="150">6</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Redirects</td>
								<td>3</td>
							</tr>
							<tr class="row">
								<td width="250">Timeouts</td>
								<td width="150">1</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Access Violations</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td width="250">Page Hits</td>
								<td width="150">73</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Form Hits</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td width="250">Total Hits</td>
								<td width="150">82</td>
							</tr>
						</table>
						<br>
						<table border="0" cellspacing="0" cellpadding="4">
							<tr class="tablehead">
								<td colspan="2" bgcolor="#BDC8DD">CIP Connection Statistics</td>
							</tr>
							<tr class="row">
								<td width="250">Current CIP Msg Connections</td>
								<td width="150">0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>CIP Msg Connection Limit</td>
								<td>128</td>
							</tr>
							<tr class="row">
								<td width="250">Max Msg Connections Observed</td>
								<td width="150">0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Current CIP I/O Connections</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td width="250">CIP I/O Connection Limit</td>
								<td width="150">128</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Max I/O Connections Observed</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td width="250">Conn Opens</td>
								<td width="150">272</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Open Errors</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td width="250">Conn Closes</td>
								<td width="150">0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Close Errors</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td width="250">Conn Timeouts</td>
								<td width="150">0</td>
							</tr>
						</table>

				</td>

				<! -- second col -->

				<td valign="top" class="subhead">


						<table border="0" cellspacing="0" cellpadding="4">
							<tr class="tablehead">
								<td colspan="2" bgcolor="#BDC8DD">TCP Connections (CIP)</td>
							</tr>
							<tr class="row">
								<td width="250">Current TCP Connections</td>
								<td width="150">0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>TCP Connection Limit</td>
								<td>64</td>
							</tr>
							<tr class="row">
								<td>Maximum Observed</td>
								<td>0</td>
							</tr>
						</table>
						<br>
						<table border="0" cellspacing="0" cellpadding="4">
							<tr class="tablehead">
								<td colspan="2" bgcolor="#BDC8DD">CIP Messaging Statistics</td>
							</tr>
							<tr class="row">
								<td width="250">Messages Sent</td>
								<td width="150">0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Messages Received</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td width="250">UCMM Sent</td>
								<td width="150">272</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>UCMM Received</td>
								<td>272</td>
							</tr>
						</table>
						<br>
						<table border="0" cellspacing="0" cellpadding="4">
							<tr class="tablehead">
								<td colspan="2" bgcolor="#BDC8DD">I/O Packet/Second Statistics</td>
							</tr>
							<tr class="row">
								<td width="250">Total</td>
								<td width="150">0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Sent</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td width="250">Received</td>
								<td width="150">0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td width="250">Inhibited</td>
								<td width="150">0</td>
							</tr>
							<tr class="row">
								<td>Rejected</td>
								<td>0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Capacity</td>
								<td>5000</td>
							</tr>
							<tr class="row">
								<td width="250">Actual Reserve</td>
								<td width="150">5000</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Theoretical Reserve</td>
								<td>5000</td>
							</tr>
						</table>
						<br>
						<table border="0" cellspacing="0" cellpadding="4">
							<tr class="tablehead">
								<td colspan="2" bgcolor="#BDC8DD">I/O Packet Counter Statistics</td>
							</tr>
							<tr class="row">
								<td width="250">Total</td>
								<td width="150">0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Sent</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td width="250">Received</td>
								<td width="150">0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Inhibited</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td width="250">Rejected</td>
								<td width="150">0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Missed</td>
								<td>0</td>
							</tr>
						</table>

				</td>
			</tr>
			<tr>
				<td colspan="2" align="center">
					<p align="center" valign="middle">
						<form onSubmit="jsRefresh(); return false;">
							Seconds Between Refresh:&#160;
							<input type="text" id="refresh" value="15" size="3" maxlength="3" style="font-size: 10;"/>
							&#160;Disable Refresh with 0.
						</form>
					</p>
				</td>
			</tr>
		</table><br>
		<!-- Do not modify below this point -->
		
		</td>
		<td width="1"><img src="images/border.gif" width="1" height="1" border="0"></td>
	</tr>
	<tr>
		<td colspan="">
		</td>
	</tr>
</table>
<br/>Copyright © 2004 Rockwell Automation, Inc. All Rights Reserved.
</div>
<!-- End body background -->
</body>
</html>
