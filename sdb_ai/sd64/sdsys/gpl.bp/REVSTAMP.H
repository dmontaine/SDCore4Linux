* REVSTAMP.H
* Revision information
* Copyright (c) 2007 Ladybridge Systems, All Rights Reserved
*
* This program is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation; either version 3, or (at your option)
* any later version.
* 
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
* 
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software Foundation,
* Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
* 
* START-HISTORY:
* rev 1.0-2 see sdsys/changelog
* rev 1.0-1 Add back PROCREAD PROCWRITE
* rev 0.9-3 Nov 25 move voc back to dynamic file 
* rev 0.9-2 Mar 25 add sdpyobj function
* rev 0.9.1 Mar 25 return to single rev track
* 31 Dec 23 SD launch - prior history suppressed
* END-HISTORY
*
* START-DESCRIPTION:
*
* END-DESCRIPTION
*
* START-CODE


* rev 0.9.1 Mar 25 return to single rev track 
* N O T E:  This file is the SOURCE.  GPL.BP/REVSTAMP.H is GENERATED from it 
* by gplbld/gen_includes.py, which "make check-includes" enforces - do not   
* hand-edit the BASIC copy.  (The old note said to edit it manually or run   
* the REVSTAMP verb; that verb reads ./gplsrc/revstamp.h and so cannot run   
* on an installed system at all.)                                           
* Also edit VOC_TEMPLATE and NEWVOC record $RELEASE                          

* ONE-LINE COMMENTS ONLY IN THIS FILE, AND THAT IS NOT A STYLE PREFERENCE. 
* gen_includes.py turns a line that OPENS a C comment into a BASIC "*"     
* comment and passes every other line through UNCHANGED, so the            
* continuation lines of a multi-line C block comment are emitted as BARE   
* BASIC.  Measured 09 Sep 26: a block comment written here compiled clean  
* in C, passed "make check-includes", and then gave 17 errors in BOTH      
* LOGIN and CPROC - every program that includes this one.                  
* Do not write a comment-opening sequence inside these comments either:    
* that is -Wcomment, and this file is built with -Wall.                    

* 09 Sep 26 dm - PRE_RELEASE 17.  THE STAMP IS THIS PROJECT'S NUMBER NOW.  
* It read "1.0-2", which is UPSTREAM's build, so the shipped binary told   
* the user it was a version of something else.                            
*                                                                         
* THE L IS THE POINT, AND IT IS THE PORT'S SHAPE.  Owner, 24 Aug 26, of    
* the Windows port: "our numbering sequence is different than upstream,    
* hence the W in front of the number."  So sdb64 at 1.0-2 and upstream dev 
* at 1.0-3 are not numbers to catch up with - the trailing digit must NOT  
* be advanced to track them, because that would imply a parity this port   
* does not claim.                                                         
*                                                                         
* MAJOR_REV, MINOR_REV AND BUILD ARE DELIBERATELY LEFT AT UPSTREAM'S       
* 1/0/2, exactly as the port leaves them.  sysseg.c:48 packs them into a   
* shared-segment compatibility word, so they are a binary interface and    
* not a name.  ONLY THE DISPLAY STRING IS OURS.                           
*                                                                         
* AND THE TWO STAMPS MUST MOVE TOGETHER OR ORDINARY LOGINS STOP.           
* LOGIN:381 is "if compare(system(1012), SD.REV.STAMP)" - system(1012)     
* returns the C value (op_sys.c:355-358) and SD.REV.STAMP is the BASIC one 
* compiled into LOGIN - and on a mismatch it displays sysmsg 5029 and      
* TERMINATES THE CONNECTION for any session that is not internal.  That is 
* why the BASIC copy is generated rather than typed.                      
$define MAJOR.REV      1
$define MINOR.REV      0
$define BUILD          2
$define SD.REV.STAMP   "L1.0-0"

$define SD.COPYRIGHT.YEAR "2007"

* END-CODE 
