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
		<td nowrap width="6" valign="top"><img src="images/menustartoff.gif" alt="" width="10" 
	  height="16" border="0" /></td>
		<td nowrap background="images/menubgoff.gif">
			<a class="tab" onClick="highlightTree('/diagover.asp');" href="diagover.asp">Diagnostic Overview</a></td>
		<td nowrap><img src="images/mensepoffoff.gif" width="23" height="16" border="0"></td>
		<td nowrap background="images/menubgoff.gif">
			<a class="tab" onClick="highlightTree('/diagnetwork.asp');" href="diagnetwork.asp">Network Settings</a></td>
		<td nowrap><img src="images/mensepoffoff.gif" width="23" height="16" border="0"></td>
		<td nowrap background="images/menubgoff.gif">
			<a class="tab" onClick="highlightTree('/msgconnect.asp');" href="msgconnect.asp">Message Connections</a></td>
		<td nowrap><img src="images/mensepoffoff.gif" width="23" height="16" border="0"></td>
		<td nowrap background="images/menubgoff.gif">
			<a class="tab" onClick="highlightTree('/ioconnect.asp');" href="ioconnect.asp">I/O Connections</a></td>
		<td nowrap><img src="images/mensepoffon.gif" width="23" height="16" border="0"></td>
		<td nowrap background="images/menubgon.gif">Ethernet Statistics</td>
		<td nowrap><img src="images/menuendon.gif" width="21" height="16" border="0"></td>
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
								<td width="200">Speed</td>
								<td width="150">100 Mbps</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Duplex</td>
								<td>Full Duplex</td>
							</tr>
							<tr class="row">
								<td>Autonegotiate Status</td>
								<td>Autonegotiate Speed and Duplex</td>
							</tr>
						</table>
						<br>
						<table border="0" cellspacing="0" cellpadding="4">
							<tr class="tablehead">
								<td colspan="2" bgcolor="#BDC8DD">Interface Counters</td>
							</tr>
							<tr class="row">
								<td width="200">In Octets</td>
								<td width="150">80873</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>In Ucast Packets</td>
								<td>523</td>
							</tr>
							<tr class="row">
								<td>In NUcast Packets</td>
								<td>285</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>In Discards</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td>In Errors</td>
								<td>0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>In Unknown Protos</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td width="200">Out Octets</td>
								<td width="150">245091</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Out Ucast Packets</td>
								<td>497</td>
							</tr>
							<tr class="row">
								<td>Out NUcast Packets</td>
								<td>348</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Out Discards</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td>Out Errors</td>
								<td>0</td>
							</tr>
						</table>
				</td>
				<td valign="top" class="subhead">

						<table border="0" cellspacing="0" cellpadding="4">
							<tr class="tablehead">
								<td colspan="2" bgcolor="#BDC8DD">Media Counters</td>
							</tr>
							<tr class="row">
								<td width="200">Alignment Errors</td>
								<td width="150">0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>FCS Errors</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td>Single Collisions</td>
								<td>0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Multiple Collisions</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td>SQE Test Errors</td>
								<td>0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Deferred Transmissions</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td>Late Collisions</td>
								<td>0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Excessive Collisions</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td>MAC Transmit Errors</td>
								<td>0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>Carrier Sense Errors</td>
								<td>0</td>
							</tr>
							<tr class="row">
								<td>Frame Too Long</td>
								<td>0</td>
							</tr>
							<tr bgcolor="#dedede">
								<td>MAC Receive Errors</td>
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
							<input type="text" id="refresh" value="15" size="1" maxlength="3" style="font-size: 10;"/>
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
