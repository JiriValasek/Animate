:: This batch file generates documentation for Animate workbench
@ECHO OFF
SET "current_directory=%CD%"
SET "scripts_directory=%CD%"
SET "output_directory=%CD%\Doxypypy outputs"
SET "doxygen_file=.\Doxyfile"

:: Sort out input arguments
SET output_dir_set=0
:while
	IF [%1]==[] (
		IF %output_dir_set% EQU 0 (
			IF NOT EXIST "%output_directory%" (
				MKDIR "%output_directory%"
			)
		) 
		GOTO :run
	) ELSE IF "%1"=="/S" (
		IF EXIST "%2" (
			CALL :set_scripts_dir %2
		) ELSE (
			ECHO Invalid path to a directory with scripts to translate. >&2
			SET /A RETURN_CODE=3
			GOTO :end
		)
	) ELSE IF "%1"=="/D" (
		IF EXIST "%2" (
			SET "doxygen_file=%2"
		) ELSE (
			ECHO Invalid path to a doxygen file. >&2
			SET /A RETURN_CODE=2
			GOTO :end
		)
	) ELSE IF "%1"=="/O" (
		IF EXIST "%2" (
			CALL :set_output_dir %2
		) ELSE (
			ECHO Invalid path to a directory for translated scripts. >&2
			SET /A RETURN_CODE=3
			GOTO :end
		)
		SET /A output_dir_set=1
	) ELSE IF "%1"=="/?" (
		GOTO :help
	)
	SHIFT
	SHIFT
	GOTO :while

:set_scripts_dir
	:: Sets scripts_directory, necessary to do as a function
	:: to accept ., .. as a path
	CD "%1"
	SET "scripts_directory=%CD%"
	CD "%current_directory%"
	EXIT /B

:set_output_dir
	:: Sets output_directory, necessary to do as a function
	:: to accept ., .. as a path
	CD "%1"
	SET "output_directory=%CD%"
	CD "%current_directory%"
	EXIT /B

:help
	:: Generate help
	ECHO Generates documentation for Animate workbench.
	ECHO;
	ECHO GenerateDocumentation [/?] [/S [directory path]] [/O [directory path]] [/D [filepath]]
	ECHO;
	ECHO(  /?      Generates help for GenerateDocumentation.
	ECHO(  /S      Specifies a directory with python scripts *.py to translate using doxypypy.
	ECHO(  /O      Specifies an output directory for translated scripts.
	ECHO(  /D      Specifies a doxygen configuration file to run.
	ECHO;
	ECHO This script tranlates python scripts and moves them into an output directory.
	ECHO Afterwards it runs a doxygen configuration file. If none of /S, /O and /D command
	ECHO switches are supplied, then python scripts are looked for in a current directory,
	ECHO the output directory is "Doxypypy outputs" folder made or existing in 
	ECHO the current directory and the doxygen configuration file is ./doxyfile.
	SET /A RETURN_CODE=0
	GOTO :end


:run
	:: Run main procedure
	IF "%scripts_directory%"=="%output_directory%" (
		ECHO Script and output directory are identical - "%scripts_directory%",
		ECHO translation aborted because doxypypy would rewritten input files.
		SET /A RETURN_CODE=1
		GOTO :end
	)
	ECHO Translating all python scripts in "%scripts_directory%".
	CD %scripts_directory%
	IF EXIST *.py (
		FOR %%a IN (*.py) DO CALL :doxypypy_file %%a
	) ELSE (
		ECHO No python scripts found. >&2
		SET /A RETURN_CODE=2
		GOTO :end
	)
	CD %current_directory%
	IF EXIST %doxygen_file% (
		ECHO Generating documentation from %doxygen_file%.
		doxygen %doxygen_file%
	) ELSE (
		ECHO Doxygen file is not available in current directory. >&2
		SET /A RETURN_CODE=2
		GOTO :end
	)
	ECHO Everything went hunky-dory.
	GOTO :end

:doxypypy_file
	:: Translate a file using doxypypy
	ECHO Doxypypy is translating "%1".
	:: Run Doxypypy in Python 3
	doxypypy -a -c %1 > "%output_directory%\%1"
	IF %ERRORLEVEL% EQU 0 (
		ECHO Translation finished successfully.
	) ELSE (
		ECHO Translation failed with an errorlevel %ERRORLEVEL% >&2
	)
	py -3 "%current_directory%\correct_doxypypy_output_file.py" "%output_directory%\%1"
	EXIT /B

:end
	:: exit orderly
	CD %current_folder%
	EXIT /B %RETURN_CODE% & ECHO ON