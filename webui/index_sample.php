<!doctype html>
<html lang="ja">
<head>
    <meta charset="utf-8">
</head>
<body>

<?php

if($_SERVER['REQUEST_METHOD'] === 'POST'){

    if(isset($_POST['function'])){
        if(isset($_POST['file_to_load'])){
            $file_to_load = $_POST['file_to_load'];
        }
        $station=$_POST['function'];
        if($station == "UPDATELIST"){
            $new_stat_list = $_POST['newlist'];
            //print($new_stat_list);
            $file_to_load = $new_stat_list;
            $cmd = "NEWLIST " . $new_stat_list . "\r\n";
            $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
            socket_connect($socket, "localhost", 8899);
            socket_write($socket, $cmd);
        } else if($station != "STOPALL"){
            $cmd = "START " . $station . "\r\n";
            $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
            socket_connect($socket, "localhost", 8899);
            socket_write($socket, $cmd);
        } else {
            $cmd = "STOP " . "\r\n";
            $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
            socket_connect($socket, "localhost", 8899);
            socket_write($socket, $cmd);
        }

    }
}


print "<table border=1 cellspacing=0 cellpadding=0>";

if (!isset($file_to_load)){
    // 初期(Webアクセス時)の局リスト
    $file_to_load = 'stations/station_list';
}
$stations = file($file_to_load);


foreach($stations as $line){
    $s_line = explode(',', $line);
    if(strcmp(trim($s_line[4]), "radiko") == 0 || strcmp(trim($s_line[4]), "radiru") == 0){
        $out_html = "<tr><td>";
        if($s_line[3] != ""){
            $out_html .= "<img src=stations/";
            $out_html .= $s_line[3];
            $out_html .= ">";
        } else {
            $out_html .= "";
        }
        $out_html .= "</td>";
        $out_html .= "<td>";
        $out_html .= '<form action="" method="POST">';
        $out_html .= '<input type="hidden" name="function" value="';
        $out_html .= $s_line[0];
        $out_html .= '">';
        $out_html .= '<input type="hidden" name="file_to_load" value="';
        $out_html .= $file_to_load;
        $out_html .= '">';
        $out_html .= '<input type="submit" value="';
        $out_html .= $s_line[1];
        $out_html .= '">';
        $out_html .= "</form>";
        $out_html .= "</td></tr>";
        print $out_html;
    }
    if(strcmp(trim($s_line[4]), "MENU") == 0){
        $out_html = "<tr><td>";
        $out_html .= "<img src=stations/";
        $out_html .= $s_line[3];
        $out_html .= ">";
        $out_html .= "</td>";
        $out_html .= "<td>";
        $out_html .= '<form action="" method="POST">';
        $out_html .= '<input type="hidden" name="function" value="UPDATELIST">';
        $out_html .= '<input type="hidden" name="newlist" value="';
        $out_html .= $s_line[0];
        $out_html .= '">';
        $out_html .= '<input type="hidden" name="file_to_load" value="';
        $out_html .= $file_to_load;
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
<input type="hidden" name="file_to_load" value="{$file_to_load}">
<input type="submit" value="停止">
</form>
</td>
</tr>
</table>

EOT

?>

</body>
</html>
