#!/bin/bash
#This Source Code Form is subject to the terms of the Mozilla
#Public License, v. 2.0. If a copy of the MPL was not distributed
#with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
if [ -z $1 ] || [ -z $2 ] || [ -z $3 ]; then
	echo "Missing arguments."
	echo "Sintax:"
	echo "./customize_installer.sh source destination file1 file2 file3 ..."
	exit 1
fi
#PTHSRC=`readlink -f $1`
#PTHDST=`readlink -f $2`
PTHSRC=$1
PTHDST=$2
if [ ! -f $PTHSRC ]; then
	echo "Missing source file: $1"
	exit 1
fi
for fn in "${@: 3}"; do    
    if [ ! -f $fn ]; then
		echo "Missing file: $fn"
		exit 1
    fi
done
echo "BEGIN"
echo "Extracting file ..."
SKIP1=`awk '/^__TARFILE_BEGIN__/ { print NR; exit 0; }' $PTHSRC`
SKIP2=`awk '/^__TARFILE_BEGIN__/ { print NR + 1; exit 0; }' $PTHSRC`
head -$SKIP1 $PTHSRC > install.sh.conf
tail -n +$SKIP2 $PTHSRC > extract.tar
echo "OK"
echo "Adding files ..."
for fn in "${@: 3}"; do    
	tar -rf extract.tar $fn
done
echo "OK"
echo "Make installer ..."
cat install.sh.conf extract.tar > $PTHDST
echo "OK"
echo "Clean..."
rm -f install.sh.conf
rm -f extract.tar
echo "OK"
echo "END"
exit 0
