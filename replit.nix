{pkgs}: {
  deps = [
    pkgs.redis
    pkgs.jq
    pkgs.libxcrypt
    pkgs.bash
    pkgs.postgresql
    pkgs.openssl
  ];
}
