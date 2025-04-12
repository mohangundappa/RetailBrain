{pkgs}: {
  deps = [
    pkgs.jq
    pkgs.libxcrypt
    pkgs.bash
    pkgs.postgresql
    pkgs.openssl
  ];
}
