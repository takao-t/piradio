<!doctype html>
<html lang="ja">
<head>
    <meta charset="utf-8">
</head>
<body>

<?php

if($_SERVER['REQUEST_METHOD'] === 'POST'){

    if(isset($_POST['function'])){
        $station=$_POST['function'];
        if($station != "STOPALL"){
            $cmd = "START:" . $station . "\r\n";
            $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
            socket_connect($socket, "localhost", 8899);
            socket_write($socket, $cmd);
        } else {
            $cmd = "STOP:" . "\r\n";
            $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
            socket_connect($socket, "localhost", 8899);
            socket_write($socket, $cmd);
        }
    }
}


print "<table border=1 cellspacing=0 cellpadding=0>";

$stations = file('stations/station_list');


foreach($stations as $line){
    $s_line = explode(',', $line);
    if(strcmp(trim($s_line[4]), "radiko") == 0){
        $out_html = "<tr><td>";
        $out_html .= "<img src=stations/";
        $out_html .= $s_line[0];
        $out_html .= ".png>";
        $out_html .= "</td>";
        $out_html .= "<td>";
        $out_html .= '<form action="" method="POST">';
        $out_html .= '<input type="hidden" name="function" value="';
        $out_html .= $s_line[0];
        $out_html .= '">';
        $out_html .= '<input type="submit" value="';
        $out_html .= $s_line[1];
        $out_html .= '">';
        $out_html .= "</form>";
        $out_html .= "</td></tr>";
        print $out_html;
    }
}


echo <<<EOT
<tr>
<td>停止</td>
<td>
<form action="" method="POST">
<input type="hidden" name="function" value="STOPALL">
<input type="submit" value="停止">
</form>
</td>
</tr>
</table>

EOT

?>

</body>
</html>
