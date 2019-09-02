SET "current_directory=%CD%"
IF EXIST ".\output scripts" (
	ECHO OK
) ELSE (
	ECHO ERROR
)
CD %current_directory%
	