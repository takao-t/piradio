<?php

$cmd = "STOP " . "\r\n";

$socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
socket_connect($socket, "localhost", 8899);
socket_write($socket, $cmd);

?>
