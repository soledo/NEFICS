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
		<td nowrap><img src="images/mensepoffon.gif" width="23" height="16" border="0"></td>
		<td nowrap background="images/menubgon.gif">I/O Connections</td>
		<td nowrap><img src="images/menseponoff.gif" width="23" height="16" border="0"></td>
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
				
					<table width="100%" cellspacing=0 cellpadding=4 border=0>
  <tr bgcolor="#bdc8dd"class="tablehead">
    <td>Conn S# / UpTime</td>
    <td>Rcv/Xmt</td>
    <td>Connection Id</td>
    <td>Source</td>
    <td>Dest</td>
    <td>Multicast Address</td>
    <td>RPI</td>
    <td>Lost</td>
    <td>Size</td>
  </tr>
</table>

						
				</td>
			</tr>
			<tr>
				<td align="center">
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
