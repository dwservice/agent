#!/bin/bash
#This Source Code Form is subject to the terms of the Mozilla
#Public License, v. 2.0. If a copy of the MPL was not distributed
#with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
if [ -z $1 ] || [ -z $2 ] || [ -z $3 ] || [ -z $4 ]; then
	echo "Missing arguments."
	echo "Sintax:"
	echo "./customize_installer_mac.sh name source destination file1 file2 file3 ..."
	exit 1
fi
#PTHSRC=`readlink -f $1`
#PTHDST=`readlink -f $2`
INAME="DWAgent"
PTHSRC=$1
PTHDST=$2
if [ ! -f $PTHSRC ]; then
	echo "Missing source file: $PTHSRC"
	exit 1
fi
for fn in "${@: 3}"; do    
    if [ ! -f $fn ]; then
		echo "Missing file: $fn"
		exit 1
    fi    
    if [ "$fn" = "install.json" ]; then
		INAMEAP=`grep \"name\" "$fn" | cut -d ':' -f 2 | cut -d '"' -f 2`
		if [ ! -z "${INAMEAP}" ]; then
			INAME=${INAMEAP}
		fi
	fi    
done
echo "BEGIN"
echo "Extracting file ..."
rm -r -f tmpextract/
mkdir tmpextract
hdiutil detach /Volumes/DWAgent/
hdiutil attach $PTHSRC
cp -R /Volumes/DWAgent/ tmpextract/
hdiutil detach /Volumes/DWAgent/
echo "OK"
echo "Adding files ..."
mkdir tmpextract/DWAgent.app/Contents/MacOS/Custom/
for fn in "${@: 3}"; do
    cp $fn tmpextract/DWAgent.app/Contents/MacOS/Custom/
done
sed -i "" "s/net\.dwservice/com\.apiremoteaccess/g" tmpextract/DWAgent.app/Contents/Info.plist
sed -i "" "s/DWAgent/$INAME/g" tmpextract/DWAgent.app/Contents/Info.plist
mv tmpextract/DWAgent.app tmpextract/$INAME.app
echo "OK"
echo "Make installer ..."
hdiutil create "$INAME.dmg" -volname "$INAME" -srcfolder tmpextract/
echo "OK"
echo "Clean..."
rm -r -f tmpextract/
echo "OK"
echo "END"
exit 0
