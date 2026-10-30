# Intermediario Sectigo DV R36

Certificado público **Sectigo Public Server Authentication CA DV R36**, emitido por **Sectigo Public Server Authentication Root R46**, válido entre 22/03/2021 y 21/03/2036.

Fuente AIA oficial: http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt . También está documentado por Sectigo en https://support.sectigo.com/Com_KnowledgeDetailPage?Id=kA0Uj0000005KHR . El servidor del Observatorio presentó solo su certificado de sitio durante la consulta del 29/10/2026. macOS resolvió su cadena, pero curl/OpenSSL en Ubuntu rechazó la ausencia del intermediario (error 60).

El archivo DER se descargó del punto AIA publicado por la propia certificadora y se convirtió a PEM. Su firma/cadena se verifica con `openssl verify -CAfile <certifi.where()>` antes de incorporarlo a un bundle temporal del runner. Las raíces independientes de confianza son las de Mozilla distribuidas por certifi, fijado en requirements.txt. No se confía en un certificado de sitio como raíz, no se instala nada en el almacén del sistema y no se desactivan la verificación TLS, las fechas ni la comprobación de nombre de host. Si la cadena deja de validar, el Action falla.
